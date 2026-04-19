## ADDED Requirements

### Requirement: Support safer request pacing
The system SHALL provide crawl pacing controls that reduce the likelihood of IP blocking during repeated requests.

#### Scenario: Run with conservative pacing
- **WHEN** the user configures a crawl with low concurrency and a non-zero request delay
- **THEN** the system MUST respect that pacing configuration for listing and detail requests

#### Scenario: Randomize request intervals
- **WHEN** pacing jitter is enabled
- **THEN** the system MUST vary the effective delay between requests within the configured jitter range instead of using a perfectly fixed interval

### Requirement: Detect probable blocking signals
The system SHALL distinguish probable blocking signals from ordinary crawl failures.

#### Scenario: HTTP block response is detected
- **WHEN** a request returns a response such as `403` or `429`
- **THEN** the system MUST classify that event as a probable blocking signal

#### Scenario: Repeated abnormal timeout pattern
- **WHEN** the crawler encounters repeated timeouts or challenge-like responses during a run
- **THEN** the system MUST record those events as probable blocking signals instead of treating them only as generic request errors

### Requirement: Back off when blocking is suspected
The system SHALL reduce request aggressiveness when probable blocking signals are detected.

#### Scenario: Apply backoff after blocking signal
- **WHEN** a probable blocking signal occurs
- **THEN** the system MUST wait longer before the next retry or follow-up request according to the configured backoff strategy

#### Scenario: Stop early after repeated blocking
- **WHEN** the number of probable blocking signals reaches the configured stop threshold
- **THEN** the system MUST stop or short-circuit the remaining crawl work for that run

### Requirement: Support proxy and browser configuration
The system SHALL allow the operator to configure proxy settings and browser type for crawl runs.

#### Scenario: Run with configured proxy
- **WHEN** the user provides a proxy endpoint and optional credentials
- **THEN** the system MUST use that proxy configuration for browser-backed crawl requests

#### Scenario: Run with alternate browser type
- **WHEN** the user specifies a supported browser type such as `chromium` or `firefox`
- **THEN** the system MUST launch the requested browser type for the crawl run

### Requirement: Report block-related behavior in crawl output
The system SHALL expose block-related outcomes in logs or run summaries so operators can understand why a crawl slowed down or stopped.

#### Scenario: Crawl completes with blocking signals
- **WHEN** a run completes after one or more probable blocking events
- **THEN** the system MUST include block-related counts or details in its output or logs

#### Scenario: Crawl stops because of block threshold
- **WHEN** the crawler aborts early due to too many probable blocking signals
- **THEN** the system MUST report that the run stopped because the block threshold was exceeded
