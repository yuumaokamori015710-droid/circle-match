"""Official SDK contract tests with an in-memory transport, never the network."""
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

import stripe

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"outputs"))
from circlematch_payments import API_VERSION, Config, StripeGateway


class Transport(stripe.HTTPClient):
    name = "local-contract-test"

    def __init__(self):
        super().__init__()
        self.calls=[]

    def request(self,method,url,headers,post_data=None,**kwargs):
        self.calls.append((method,url,headers,parse_qs(post_data or "")))
        return json.dumps({"id":"local_result","object":"account"}),200,{}


class SDKTests(unittest.TestCase):
    def setUp(self):
        self.config=Config(True,"test","sk_test_local_contract","whsec_platform_local","acct_platform",
                           connect_webhook_secret="whsec_connect_local")
        self.transport=Transport()
        with patch.object(stripe,"RequestsClient",return_value=self.transport):
            self.gateway=StripeGateway(self.config)

    def test_versions_and_destination_parameters(self):
        self.assertEqual(stripe.VERSION,"16.0.0")
        self.gateway.create_session({"mode":"payment","payment_method_types":["card"],
            "payment_intent_data":{"application_fee_amount":600,"transfer_data":{"destination":"acct_host"}},
            "line_items":[{"price_data":{"currency":"jpy","unit_amount":2000,"product_data":{"name":"Test"}},"quantity":3}]},"stable-order-key")
        method,url,headers,data=self.transport.calls[-1]
        lower={k.lower():v for k,v in headers.items()}
        self.assertEqual(lower["stripe-version"],API_VERSION)
        self.assertEqual(lower["idempotency-key"],"stable-order-key")
        self.assertTrue(url.endswith("/v1/checkout/sessions"))
        self.assertEqual(data["payment_intent_data[application_fee_amount]"],["600"])
        self.assertEqual(data["payment_intent_data[transfer_data][destination]"],["acct_host"])
        self.assertEqual(data["line_items[0][quantity]"],["3"])
        self.assertFalse(any("on_behalf_of" in k for k in data))

    def test_hosted_account_and_refund_contract(self):
        self.gateway.create_account("account-key")
        data=self.transport.calls[-1][3]
        self.assertEqual(data["controller[fees][payer]"],["application"])
        self.assertEqual(data["controller[losses][payments]"],["application"])
        self.assertEqual(data["metadata[circlematch_create_key]"],["account-key"])
        self.gateway.refund("ch_local","refund-key")
        data=self.transport.calls[-1][3]
        self.assertEqual(data["reverse_transfer"],["true"])
        self.assertEqual(data["refund_application_fee"],["true"])
        self.assertNotIn("amount",data)
        self.gateway.account_link("acct_host")
        self.assertEqual(self.transport.calls[-1][3]["type"],["account_onboarding"])

    def test_real_sdk_raw_signature_and_separate_endpoints(self):
        body=json.dumps({"id":"evt_local","object":"event","type":"account.updated","data":{"object":{"id":"acct_host"}}}).encode()
        timestamp=str(int(time.time()))
        def signature(secret):
            return "t="+timestamp+",v1="+hmac.new(secret.encode(),timestamp.encode()+b"."+body,hashlib.sha256).hexdigest()
        self.assertEqual(self.gateway.verify(body,signature(self.config.webhook_secret))["id"],"evt_local")
        self.assertEqual(self.gateway.verify(body,signature(self.config.connect_webhook_secret),True)["id"],"evt_local")
        with self.assertRaises(stripe.SignatureVerificationError):
            self.gateway.verify(body+b" ",signature(self.config.webhook_secret))
        with self.assertRaises(stripe.SignatureVerificationError):
            self.gateway.verify(body,signature(self.config.webhook_secret),True)
        self.assertEqual(self.transport.calls,[])


if __name__=="__main__":
    unittest.main()
