--
-- PostgreSQL database dump
--

\restrict AREU1fhakcI0Dxh2empGAnrCVJdtzdmuR72UwnP90pYgDnAoHTssUZEqSOLYus9

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    name_ko character varying(100),
    slug character varying(100) NOT NULL,
    color character varying(7) DEFAULT '#3B82F6'::character varying,
    icon character varying(50),
    parent_id integer,
    sort_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: connection_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.connection_sources (
    id integer NOT NULL,
    connection_id integer,
    source_id integer,
    mention_context text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: connection_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.connection_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: connection_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.connection_sources_id_seq OWNED BY public.connection_sources.id;


--
-- Name: entity_properties; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entity_properties (
    id integer NOT NULL,
    entity_type character varying(20) NOT NULL,
    entity_id integer NOT NULL,
    property character varying(10) NOT NULL,
    property_name character varying(100),
    value_type character varying(20),
    value_qid character varying(20),
    value_string text,
    value_year integer,
    value_quantity numeric,
    value_lat numeric(10,7),
    value_lon numeric(10,7),
    qualifier_start_year integer,
    qualifier_end_year integer,
    wikidata_id character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: entity_properties_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entity_properties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_properties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entity_properties_id_seq OWNED BY public.entity_properties.id;


--
-- Name: event_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_connections (
    id integer NOT NULL,
    event_a_id integer NOT NULL,
    event_b_id integer NOT NULL,
    direction character varying(20) NOT NULL,
    layer_type character varying(20) NOT NULL,
    layer_entity_id integer,
    connection_type character varying(50),
    strength_score double precision DEFAULT 0,
    source_count integer DEFAULT 0,
    time_distance integer,
    manual_strength double precision,
    manual_reason text,
    verification_status character varying(20) DEFAULT 'unverified'::character varying,
    verified_by character varying(50),
    verified_at timestamp without time zone,
    curated_status character varying(20),
    curated_by integer,
    curated_at timestamp without time zone,
    curation_note text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: event_connections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_connections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_connections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_connections_id_seq OWNED BY public.event_connections.id;


--
-- Name: event_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_locations (
    event_id integer NOT NULL,
    location_id integer NOT NULL,
    role character varying(50) DEFAULT 'location'::character varying
);


--
-- Name: event_participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_participants (
    id integer NOT NULL,
    event_id integer NOT NULL,
    participant_type character varying(20) NOT NULL,
    participant_id integer NOT NULL,
    role character varying(50) DEFAULT 'participant'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: event_participants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_participants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_participants_id_seq OWNED BY public.event_participants.id;


--
-- Name: event_persons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_persons (
    event_id integer NOT NULL,
    person_id integer NOT NULL,
    role character varying(100),
    description text
);


--
-- Name: event_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_sources (
    event_id integer NOT NULL,
    source_id integer NOT NULL,
    page_reference character varying(100),
    quote text
);


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id integer NOT NULL,
    wikidata_id character varying(20),
    title character varying(500) NOT NULL,
    title_ko character varying(500),
    date_start integer,
    date_end integer,
    date_precision character varying(20) DEFAULT 'year'::character varying,
    event_type character varying(100),
    parent_event_id integer,
    hierarchy_level integer DEFAULT 3,
    primary_location_id integer,
    description text,
    description_model character varying(50),
    description_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    certainty character varying(20),
    parent_status character varying(20),
    slug character varying(500),
    importance integer DEFAULT 3,
    connection_count integer DEFAULT 0,
    category_id integer,
    source_reliability integer DEFAULT 3,
    image_url character varying(500),
    wikipedia_url character varying(500),
    temporal_scale character varying(20),
    is_aggregate boolean DEFAULT false,
    aggregate_type character varying(50),
    default_collapsed boolean DEFAULT false,
    min_zoom_level double precision DEFAULT 1.0,
    description_ko text,
    description_ja text,
    title_ja character varying(500),
    description_source character varying(50),
    description_source_url character varying(500),
    date_start_month integer,
    date_start_day integer,
    date_end_month integer,
    date_end_day integer,
    period_id integer,
    enriched_by character varying(100),
    enriched_at timestamp without time zone,
    enrichment_version character varying(50),
    is_light boolean DEFAULT false
);


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: group_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    person_id integer NOT NULL,
    valid_from integer,
    valid_until integer,
    role character varying(100),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_members_id_seq OWNED BY public.group_members.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    wikidata_id character varying(20),
    name character varying(255) NOT NULL,
    name_ko character varying(255),
    group_type character varying(50) NOT NULL,
    founded_year integer,
    dissolved_year integer,
    territory_id integer,
    description text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.links (
    id integer NOT NULL,
    from_type character varying(20) NOT NULL,
    from_id integer NOT NULL,
    to_type character varying(20) NOT NULL,
    to_id integer NOT NULL,
    category character varying(100),
    date_start integer,
    date_end integer,
    evidence text,
    evidence_model character varying(50),
    evidence_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: links_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.links_id_seq OWNED BY public.links.id;


--
-- Name: location_names; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.location_names (
    id integer NOT NULL,
    location_id integer NOT NULL,
    name character varying(255) NOT NULL,
    name_ko character varying(255),
    valid_from integer,
    valid_until integer,
    language character varying(10) DEFAULT 'en'::character varying,
    is_primary boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: location_names_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.location_names_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: location_names_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.location_names_id_seq OWNED BY public.location_names.id;


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    id integer NOT NULL,
    wikidata_id character varying(20),
    name character varying(255) NOT NULL,
    name_ko character varying(255),
    latitude numeric(10,7) NOT NULL,
    longitude numeric(10,7) NOT NULL,
    location_type character varying(50) DEFAULT 'point'::character varying,
    parent_location_id integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    name_original character varying(255),
    modern_name character varying(255),
    country character varying(100),
    region character varying(100),
    is_region boolean DEFAULT false,
    coords_source character varying(20),
    canonical_id integer,
    hierarchy_level character varying(30),
    modern_parent_id integer,
    historical_parent_id integer,
    valid_from integer,
    valid_until integer,
    parent_id integer,
    display_level integer DEFAULT 3,
    display_zoom_min double precision DEFAULT 0,
    display_zoom_max double precision DEFAULT 10,
    description text,
    description_ko text,
    description_ja text,
    name_ja character varying(255),
    description_source character varying(50),
    description_source_url character varying(500),
    wikipedia_url character varying(500),
    geocoded_by character varying(100),
    geocoded_at timestamp without time zone,
    connection_count integer DEFAULT 0,
    type character varying(50),
    is_light boolean DEFAULT false
);


--
-- Name: locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.locations_id_seq OWNED BY public.locations.id;


--
-- Name: mentions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mentions (
    id integer NOT NULL,
    source_id integer NOT NULL,
    target_type character varying(20) NOT NULL,
    target_id integer NOT NULL,
    evidence_raw text NOT NULL,
    position_start integer,
    position_end integer,
    created_at timestamp without time zone DEFAULT now(),
    paragraph_index integer,
    link_text character varying(500)
);


--
-- Name: mentions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mentions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mentions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mentions_id_seq OWNED BY public.mentions.id;


--
-- Name: periods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.periods (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    name_ko character varying(200),
    slug character varying(200),
    year_start integer NOT NULL,
    year_end integer,
    scale character varying(20) DEFAULT 'conjuncture'::character varying,
    parent_id integer,
    description text,
    description_ko text,
    is_manual boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: periods_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.periods_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: periods_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.periods_id_seq OWNED BY public.periods.id;


--
-- Name: persons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persons (
    id integer NOT NULL,
    wikidata_id character varying(20),
    name character varying(255) NOT NULL,
    name_ko character varying(255),
    name_original character varying(255),
    birth_year integer,
    death_year integer,
    birthplace_id integer,
    deathplace_id integer,
    description text,
    description_model character varying(50),
    description_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    slug character varying(255),
    birth_month integer,
    birth_day integer,
    death_month integer,
    death_day integer,
    birth_date_precision character varying(20),
    death_date_precision character varying(20),
    biography text,
    biography_ko text,
    biography_ja text,
    name_ja character varying(255),
    biography_source character varying(50),
    biography_source_url character varying(500),
    category_id integer,
    image_url character varying(500),
    wikipedia_url character varying(500),
    canonical_id integer,
    role character varying(255),
    era character varying(100),
    floruit_start integer,
    floruit_end integer,
    certainty character varying(20),
    primary_polity_id integer,
    mention_count integer DEFAULT 0,
    avg_confidence double precision DEFAULT 0.0,
    connection_count integer DEFAULT 0,
    enriched_by character varying(100),
    enriched_at timestamp without time zone,
    enrichment_version character varying(50),
    data_quality character varying(50),
    source_type character varying(50),
    verified_at timestamp without time zone,
    is_light boolean DEFAULT false
);


--
-- Name: persons_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persons_id_seq OWNED BY public.persons.id;


--
-- Name: qrank; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qrank (
    wikidata_id character varying(20) NOT NULL,
    score bigint NOT NULL
);


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    id integer NOT NULL,
    source_type character varying(20) NOT NULL,
    title character varying(500) NOT NULL,
    author character varying(255),
    publication_year integer,
    original_year integer,
    language character varying(10) DEFAULT 'en'::character varying,
    content_raw text NOT NULL,
    chapter character varying(200),
    chunk_index integer,
    url text,
    wikidata_id character varying(20),
    gutenberg_id integer,
    reliability integer DEFAULT 3,
    created_at timestamp without time zone DEFAULT now(),
    link_count integer,
    content_html text,
    word_count integer
);


--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: territories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.territories (
    id integer NOT NULL,
    wikidata_id character varying(20),
    name character varying(255) NOT NULL,
    name_ko character varying(255),
    territory_type character varying(50) NOT NULL,
    founded_year integer,
    dissolved_year integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: territories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.territories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: territories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.territories_id_seq OWNED BY public.territories.id;


--
-- Name: territory_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.territory_locations (
    id integer NOT NULL,
    territory_id integer NOT NULL,
    location_id integer NOT NULL,
    valid_from integer,
    valid_until integer,
    relation_type character varying(50) DEFAULT 'contains'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: territory_locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.territory_locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: territory_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.territory_locations_id_seq OWNED BY public.territory_locations.id;


--
-- Name: text_mentions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.text_mentions (
    id integer NOT NULL,
    entity_type character varying(20) NOT NULL,
    entity_id integer,
    source_id integer,
    mention_text character varying(500) NOT NULL,
    context text,
    position_start integer,
    position_end integer,
    confidence double precision DEFAULT 0.0,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: text_mentions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.text_mentions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: text_mentions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.text_mentions_id_seq OWNED BY public.text_mentions.id;


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: connection_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_sources ALTER COLUMN id SET DEFAULT nextval('public.connection_sources_id_seq'::regclass);


--
-- Name: entity_properties id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_properties ALTER COLUMN id SET DEFAULT nextval('public.entity_properties_id_seq'::regclass);


--
-- Name: event_connections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_connections ALTER COLUMN id SET DEFAULT nextval('public.event_connections_id_seq'::regclass);


--
-- Name: event_participants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_participants ALTER COLUMN id SET DEFAULT nextval('public.event_participants_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members ALTER COLUMN id SET DEFAULT nextval('public.group_members_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: links id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.links ALTER COLUMN id SET DEFAULT nextval('public.links_id_seq'::regclass);


--
-- Name: location_names id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_names ALTER COLUMN id SET DEFAULT nextval('public.location_names_id_seq'::regclass);


--
-- Name: locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations ALTER COLUMN id SET DEFAULT nextval('public.locations_id_seq'::regclass);


--
-- Name: mentions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mentions ALTER COLUMN id SET DEFAULT nextval('public.mentions_id_seq'::regclass);


--
-- Name: periods id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.periods ALTER COLUMN id SET DEFAULT nextval('public.periods_id_seq'::regclass);


--
-- Name: persons id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons ALTER COLUMN id SET DEFAULT nextval('public.persons_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: territories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territories ALTER COLUMN id SET DEFAULT nextval('public.territories_id_seq'::regclass);


--
-- Name: territory_locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territory_locations ALTER COLUMN id SET DEFAULT nextval('public.territory_locations_id_seq'::regclass);


--
-- Name: text_mentions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.text_mentions ALTER COLUMN id SET DEFAULT nextval('public.text_mentions_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: categories categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_slug_key UNIQUE (slug);


--
-- Name: connection_sources connection_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_sources
    ADD CONSTRAINT connection_sources_pkey PRIMARY KEY (id);


--
-- Name: entity_properties entity_properties_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entity_properties
    ADD CONSTRAINT entity_properties_pkey PRIMARY KEY (id);


--
-- Name: event_connections event_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_connections
    ADD CONSTRAINT event_connections_pkey PRIMARY KEY (id);


--
-- Name: event_locations event_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_locations
    ADD CONSTRAINT event_locations_pkey PRIMARY KEY (event_id, location_id);


--
-- Name: event_participants event_participants_event_id_participant_type_participant_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_participants
    ADD CONSTRAINT event_participants_event_id_participant_type_participant_id_key UNIQUE (event_id, participant_type, participant_id, role);


--
-- Name: event_participants event_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_participants
    ADD CONSTRAINT event_participants_pkey PRIMARY KEY (id);


--
-- Name: event_persons event_persons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_persons
    ADD CONSTRAINT event_persons_pkey PRIMARY KEY (event_id, person_id);


--
-- Name: event_sources event_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_sources
    ADD CONSTRAINT event_sources_pkey PRIMARY KEY (event_id, source_id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: events events_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: group_members group_members_group_id_person_id_valid_from_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_person_id_valid_from_key UNIQUE (group_id, person_id, valid_from);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: groups groups_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: links links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);


--
-- Name: location_names location_names_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_names
    ADD CONSTRAINT location_names_pkey PRIMARY KEY (id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: locations locations_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: mentions mentions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mentions
    ADD CONSTRAINT mentions_pkey PRIMARY KEY (id);


--
-- Name: periods periods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.periods
    ADD CONSTRAINT periods_pkey PRIMARY KEY (id);


--
-- Name: periods periods_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.periods
    ADD CONSTRAINT periods_slug_key UNIQUE (slug);


--
-- Name: persons persons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT persons_pkey PRIMARY KEY (id);


--
-- Name: persons persons_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT persons_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: qrank qrank_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qrank
    ADD CONSTRAINT qrank_pkey PRIMARY KEY (wikidata_id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: sources sources_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: territories territories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territories
    ADD CONSTRAINT territories_pkey PRIMARY KEY (id);


--
-- Name: territories territories_wikidata_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territories
    ADD CONSTRAINT territories_wikidata_id_key UNIQUE (wikidata_id);


--
-- Name: territory_locations territory_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territory_locations
    ADD CONSTRAINT territory_locations_pkey PRIMARY KEY (id);


--
-- Name: territory_locations territory_locations_territory_id_location_id_valid_from_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territory_locations
    ADD CONSTRAINT territory_locations_territory_id_location_id_valid_from_key UNIQUE (territory_id, location_id, valid_from);


--
-- Name: text_mentions text_mentions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.text_mentions
    ADD CONSTRAINT text_mentions_pkey PRIMARY KEY (id);


--
-- Name: event_connections uq_event_connection_layer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_connections
    ADD CONSTRAINT uq_event_connection_layer UNIQUE (event_a_id, event_b_id, layer_type);


--
-- Name: idx_conn_events; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conn_events ON public.event_connections USING btree (event_a_id, event_b_id);


--
-- Name: idx_conn_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conn_layer ON public.event_connections USING btree (layer_type, layer_entity_id);


--
-- Name: idx_conn_strength; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conn_strength ON public.event_connections USING btree (strength_score);


--
-- Name: idx_ep_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ep_entity ON public.entity_properties USING btree (entity_type, entity_id);


--
-- Name: idx_ep_person_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ep_person_key ON public.entity_properties USING btree (entity_id, property) WHERE ((entity_type)::text = 'person'::text);


--
-- Name: idx_ep_property; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ep_property ON public.entity_properties USING btree (property);


--
-- Name: idx_ep_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ep_wikidata ON public.entity_properties USING btree (wikidata_id);


--
-- Name: idx_event_locations_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_locations_location ON public.event_locations USING btree (location_id);


--
-- Name: idx_event_participants_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_participants_event ON public.event_participants USING btree (event_id);


--
-- Name: idx_event_participants_participant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_participants_participant ON public.event_participants USING btree (participant_type, participant_id);


--
-- Name: idx_event_persons_person; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_event_persons_person ON public.event_persons USING btree (person_id);


--
-- Name: idx_events_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_dates ON public.events USING btree (date_start, date_end);


--
-- Name: idx_events_is_light; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_is_light ON public.events USING btree (is_light) WHERE (is_light = true);


--
-- Name: idx_events_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_location ON public.events USING btree (primary_location_id);


--
-- Name: idx_events_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_parent ON public.events USING btree (parent_event_id);


--
-- Name: idx_events_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_type ON public.events USING btree (event_type);


--
-- Name: idx_events_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_wikidata ON public.events USING btree (wikidata_id);


--
-- Name: idx_group_members_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_group_members_group ON public.group_members USING btree (group_id);


--
-- Name: idx_group_members_person; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_group_members_person ON public.group_members USING btree (person_id);


--
-- Name: idx_groups_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_groups_name ON public.groups USING btree (name);


--
-- Name: idx_groups_territory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_groups_territory ON public.groups USING btree (territory_id);


--
-- Name: idx_groups_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_groups_type ON public.groups USING btree (group_type);


--
-- Name: idx_groups_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_groups_wikidata ON public.groups USING btree (wikidata_id);


--
-- Name: idx_links_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_links_category ON public.links USING btree (category);


--
-- Name: idx_links_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_links_from ON public.links USING btree (from_type, from_id);


--
-- Name: idx_links_to; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_links_to ON public.links USING btree (to_type, to_id);


--
-- Name: idx_location_names_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_names_location ON public.location_names USING btree (location_id);


--
-- Name: idx_location_names_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_names_period ON public.location_names USING btree (valid_from, valid_until);


--
-- Name: idx_locations_coords; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_coords ON public.locations USING btree (latitude, longitude);


--
-- Name: idx_locations_is_light; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_is_light ON public.locations USING btree (is_light) WHERE (is_light = true);


--
-- Name: idx_locations_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_name ON public.locations USING btree (name);


--
-- Name: idx_locations_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_parent ON public.locations USING btree (parent_location_id);


--
-- Name: idx_locations_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_wikidata ON public.locations USING btree (wikidata_id);


--
-- Name: idx_mentions_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mentions_source ON public.mentions USING btree (source_id);


--
-- Name: idx_mentions_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mentions_target ON public.mentions USING btree (target_type, target_id);


--
-- Name: idx_persons_birthplace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persons_birthplace ON public.persons USING btree (birthplace_id);


--
-- Name: idx_persons_is_light; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persons_is_light ON public.persons USING btree (is_light) WHERE (is_light = true);


--
-- Name: idx_persons_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persons_name ON public.persons USING btree (name);


--
-- Name: idx_persons_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persons_wikidata ON public.persons USING btree (wikidata_id);


--
-- Name: idx_persons_years; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persons_years ON public.persons USING btree (birth_year, death_year);


--
-- Name: idx_qrank_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qrank_score ON public.qrank USING btree (score DESC);


--
-- Name: idx_sources_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sources_title ON public.sources USING btree (title);


--
-- Name: idx_sources_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sources_type ON public.sources USING btree (source_type);


--
-- Name: idx_sources_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sources_wikidata ON public.sources USING btree (wikidata_id);


--
-- Name: idx_territories_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_territories_name ON public.territories USING btree (name);


--
-- Name: idx_territories_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_territories_type ON public.territories USING btree (territory_type);


--
-- Name: idx_territories_wikidata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_territories_wikidata ON public.territories USING btree (wikidata_id);


--
-- Name: idx_territory_locations_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_territory_locations_location ON public.territory_locations USING btree (location_id);


--
-- Name: idx_territory_locations_territory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_territory_locations_territory ON public.territory_locations USING btree (territory_id);


--
-- Name: categories categories_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.categories(id);


--
-- Name: connection_sources connection_sources_connection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_sources
    ADD CONSTRAINT connection_sources_connection_id_fkey FOREIGN KEY (connection_id) REFERENCES public.event_connections(id) ON DELETE CASCADE;


--
-- Name: connection_sources connection_sources_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.connection_sources
    ADD CONSTRAINT connection_sources_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: event_connections event_connections_event_a_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_connections
    ADD CONSTRAINT event_connections_event_a_id_fkey FOREIGN KEY (event_a_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_connections event_connections_event_b_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_connections
    ADD CONSTRAINT event_connections_event_b_id_fkey FOREIGN KEY (event_b_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_locations event_locations_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_locations
    ADD CONSTRAINT event_locations_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_locations event_locations_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_locations
    ADD CONSTRAINT event_locations_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: event_participants event_participants_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_participants
    ADD CONSTRAINT event_participants_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_persons event_persons_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_persons
    ADD CONSTRAINT event_persons_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_persons event_persons_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_persons
    ADD CONSTRAINT event_persons_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: event_sources event_sources_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_sources
    ADD CONSTRAINT event_sources_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: event_sources event_sources_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_sources
    ADD CONSTRAINT event_sources_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: events events_parent_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_parent_event_id_fkey FOREIGN KEY (parent_event_id) REFERENCES public.events(id);


--
-- Name: events events_primary_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_primary_location_id_fkey FOREIGN KEY (primary_location_id) REFERENCES public.locations(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.persons(id) ON DELETE CASCADE;


--
-- Name: groups groups_territory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_territory_id_fkey FOREIGN KEY (territory_id) REFERENCES public.territories(id);


--
-- Name: location_names location_names_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_names
    ADD CONSTRAINT location_names_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: locations locations_parent_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_parent_location_id_fkey FOREIGN KEY (parent_location_id) REFERENCES public.locations(id);


--
-- Name: mentions mentions_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mentions
    ADD CONSTRAINT mentions_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: periods periods_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.periods
    ADD CONSTRAINT periods_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.periods(id);


--
-- Name: persons persons_birthplace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT persons_birthplace_id_fkey FOREIGN KEY (birthplace_id) REFERENCES public.locations(id);


--
-- Name: persons persons_deathplace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT persons_deathplace_id_fkey FOREIGN KEY (deathplace_id) REFERENCES public.locations(id);


--
-- Name: territory_locations territory_locations_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territory_locations
    ADD CONSTRAINT territory_locations_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: territory_locations territory_locations_territory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.territory_locations
    ADD CONSTRAINT territory_locations_territory_id_fkey FOREIGN KEY (territory_id) REFERENCES public.territories(id) ON DELETE CASCADE;


--
-- Name: text_mentions text_mentions_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.text_mentions
    ADD CONSTRAINT text_mentions_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id);


--
-- PostgreSQL database dump complete
--

\unrestrict AREU1fhakcI0Dxh2empGAnrCVJdtzdmuR72UwnP90pYgDnAoHTssUZEqSOLYus9

