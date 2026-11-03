"""Official SDK contract tests with an in-memory transport, never the network."""
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
import unittest
from dataclasses import replace
from unittest.mock import patch
from urllib.parse import parse_qs

import stripe

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"outputs"))
from circlematch_payments import API_VERSION, Config, StripeGateway, Unavailable


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

    def test_restricted_keys_preserve_mode_and_live_approval_guards(self):
        for mode in ("test", "live"):
            for prefix in ("sk_", "rk_"):
                config=replace(self.config,mode=mode,key=prefix+mode+"_local_contract",
                               base_url="https://circle-match.jp",live_approved=True)
                config.validate_new_payments()
                self.assertTrue(config.key_matches_mode())
                opposite="test" if mode=="live" else "live"
                with self.assertRaises(Unavailable):replace(config,key=prefix+opposite+"_local_contract").validate()
                if mode=="live":
                    with self.assertRaises(Unavailable):replace(config,live_approved=False).validate()
                    with self.assertRaises(Unavailable):replace(config,base_url="http://example.test").validate()
        for key in ("pk_test_local", "rk_invalid_local", "", "not_a_key"):
            config=replace(self.config,key=key)
            self.assertFalse(config.key_matches_mode())
            self.assertFalse(next(c["ok"] for c in config.connection_checks() if c["label"]=="秘密鍵とモードの一致"))
            with self.assertRaises(Unavailable):config.validate()

    def test_restricted_key_is_passed_to_sdk_without_extra_permissions(self):
        config=replace(self.config,key="rk_test_local_contract")
        with patch.object(stripe,"RequestsClient",return_value=self.transport):
            gateway=StripeGateway(config)
        gateway.platform()
        method,url,headers,data=self.transport.calls[-1]
        self.assertEqual(method.lower(),"get")
        self.assertTrue(url.endswith("/v1/account"))
        self.assertEqual({k.lower():v for k,v in headers.items()}["authorization"],"Bearer rk_test_local_contract")
        self.assertEqual(data,{})

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
