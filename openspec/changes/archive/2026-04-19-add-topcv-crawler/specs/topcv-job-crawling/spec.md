## ADDED Requirements

### Requirement: Crawl job listings from TopCV seeds
The system SHALL accept one or more `topcv.vn` job listing seed URLs and discover job detail URLs from those pages within a bounded crawl scope.

#### Scenario: Discover job detail links from a listing page
- **WHEN** the user runs the crawler with a valid TopCV listing seed URL
- **THEN** the system MUST request the listing page and collect candidate job detail URLs from that page

#### Scenario: Respect crawl bounds
- **WHEN** the crawler is configured with a page limit or job limit
- **THEN** the system MUST stop discovering additional URLs after the configured bound is reached

### Requirement: Extract normalized job detail records
The system SHALL visit each discovered TopCV job detail URL and produce a normalized record containing at least the source URL, title, company name, location, salary, description, requirements, benefits, crawl time, and source site identifier.

#### Scenario: Extract a complete job record
- **WHEN** a job detail page exposes the expected recruitment content
- **THEN** the system MUST return a structured record with the required fields mapped into the normalized output schema

#### Scenario: Preserve missing optional values
- **WHEN** a job detail page omits one or more non-core fields such as salary or benefits
- **THEN** the system MUST keep the missing fields in the output record with an empty or `null` value instead of dropping the record

### Requirement: Prevent duplicate job outputs
The system SHALL avoid emitting duplicate job records within the same crawl run.

#### Scenario: Duplicate URL appears in multiple listings
- **WHEN** the same job detail URL is discovered from multiple listing pages
- **THEN** the system MUST emit only one normalized job record for that URL in the crawl output

### Requirement: Continue when individual pages fail
The system SHALL continue processing remaining job URLs when an individual listing or detail page fails, unless the failure prevents crawler bootstrap.

#### Scenario: One detail page cannot be extracted
- **WHEN** a single job detail page returns an error, timeout, or unparsable content
- **THEN** the system MUST record the failure and continue processing the remaining discovered job URLs

#### Scenario: Seed bootstrap fails
- **WHEN** the crawler cannot access any configured seed URL
- **THEN** the system MUST fail the run with an explicit bootstrap error instead of reporting a successful crawl

### Requirement: Export crawl results in a structured format
The system SHALL write crawl results to a structured output format that preserves one normalized record per job.

#### Scenario: Successful crawl export
- **WHEN** the crawler completes with one or more extracted job records
- **THEN** the system MUST persist the results in the configured structured output format for later reuse
