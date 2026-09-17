-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.unit_entries (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id text NOT NULL,
  total_units numeric NOT NULL,
  message_id text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT unit_entries_pkey PRIMARY KEY (id)
);
CREATE TABLE public.unit_results (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id text NOT NULL,
  total_units numeric NOT NULL,
  message_id text NOT NULL,
  result text NOT NULL CHECK (result = ANY (ARRAY['win'::text, 'loss'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT unit_results_pkey PRIMARY KEY (id)
);
CREATE TABLE public.unit_entries_archive (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id text NOT NULL,
  total_units numeric NOT NULL,
  message_id text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT unit_entries_archive_pkey PRIMARY KEY (id)
);
CREATE TABLE public.unit_results_archive (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id text NOT NULL,
  total_units numeric NOT NULL,
  message_id text NOT NULL,
  result text NOT NULL CHECK (result = ANY (ARRAY['win'::text, 'loss'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT unit_results_archive_pkey PRIMARY KEY (id)
);
CREATE TABLE public.playmakers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id text NOT NULL UNIQUE,
  display_name text,
  image_path text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT playmakers_pkey PRIMARY KEY (id)
);