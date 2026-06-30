-- Circle Match master schema
-- Designed to separate public facts from personal data and internal notes.

create table universities (
  university_id text primary key,
  university_name text not null,
  prefecture text not null,
  city text,
  campus_name text,
  official_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create type circle_source_type as enum (
  'university_official',
  'self_registered',
  'public_sns',
  'other'
);

create type circle_verification_status as enum (
  'unverified',
  'claimed',
  'university_verified',
  'admin_verified'
);

create type public_status as enum (
  'draft',
  'published',
  'hidden'
);

create table circles (
  circle_id text primary key,
  university_id text not null references universities(university_id),
  circle_name text not null,
  sport_category text not null,
  activity_area text,
  source_type circle_source_type not null default 'other',
  source_url text,
  verification_status circle_verification_status not null default 'unverified',
  public_status public_status not null default 'draft',
  last_checked_at date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table circle_private_profiles (
  profile_id text primary key,
  circle_id text not null references circles(circle_id) on delete cascade,
  public_sns_url text,
  internal_notes text,
  consent_status text not null default 'not_applicable',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(circle_id)
);

create table circle_claims (
  claim_id text primary key,
  circle_id text not null references circles(circle_id) on delete cascade,
  claimant_name text,
  claimant_email text not null,
  university_email_verified boolean not null default false,
  status text not null default 'pending',
  evidence_url text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table match_posts (
  match_post_id text primary key,
  circle_id text not null references circles(circle_id),
  match_type text not null,
  level_label text not null,
  scheduled_at timestamptz not null,
  place text not null,
  conditions text,
  status text not null default 'open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_circles_university_id on circles(university_id);
create index idx_circles_sport_category on circles(sport_category);
create index idx_circles_verification_status on circles(verification_status);
create index idx_circle_private_profiles_circle_id on circle_private_profiles(circle_id);
create index idx_circle_claims_circle_id on circle_claims(circle_id);
create index idx_circle_claims_status on circle_claims(status);
create index idx_match_posts_circle_id on match_posts(circle_id);
create index idx_match_posts_scheduled_at on match_posts(scheduled_at);
