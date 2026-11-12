

\# Learning Analytics Platform - Metric Definitions



\## 1. Introduction



This document defines the metrics used to measure learner engagement, course progress, assessment performance and cohort outcomes.



All metrics must be calculated from validated source records stored in the database.



The dashboard must not use hardcoded metric values.



\## 2. Learner Metrics



\### 2.1 Total Learners

\- Definition: Total number of registered learner records.

\- Source: learners.

\- Calculation: COUNT(DISTINCT learner\_id).



\### 2.2 Active Learners

\- Definition: Learners whose current status is ACTIVE.

\- Source: learners.

\- Calculation: COUNT(DISTINCT learner\_id) WHERE learner\_status = 'ACTIVE'.



\### 2.3 Inactive Learners

\- Definition: Learners whose current status is INACTIVE.

\- Source: learners.

\- Calculation: COUNT(DISTINCT learner\_id) WHERE learner\_status = 'INACTIVE'.



\### 2.4 Suspended Learners

\- Definition: Learners whose current status is SUSPENDED.

\- Source: learners.

\- Calculation: COUNT(DISTINCT learner\_id) WHERE learner\_status = 'SUSPENDED'.



\## 3. Course Metrics



\### 3.1 Total Courses

\- Definition: Total number of available course records.

\- Source: courses.

\- Calculation: COUNT(DISTINCT course\_id).



\### 3.2 Published Courses

\- Definition: Courses currently published.

\- Source: courses.

\- Calculation: COUNT(DISTINCT course\_id) WHERE course\_status = 'PUBLISHED'.



\### 3.3 Course Enrollment Count

\- Definition: Number of enrollments associated with a course.

\- Source: enrollments.

\- Calculation: COUNT(DISTINCT enrollment\_id) grouped by course\_id.



\### 3.4 Course Completion Rate

\- Definition: Percentage of eligible enrollments that have completed a course.

\- Source: enrollments and course\_outcomes.

\- Calculation:



&#x20; Completion Rate = (Completed Enrollments / Eligible Enrollments) \* 100



\- Completed enrollments are those with outcome\_status = 'COMPLETED'.

\- The reporting window and eligible enrollment population must be defined consistently.



\## 4. Learner Engagement Metrics



\### 4.1 Weekly Active Learners

\- Definition: Unique learners with at least one valid activity event during a reporting week.

\- Source: activity\_events.

\- Calculation: COUNT(DISTINCT learner\_id) grouped by week.

\- Use event\_time\_utc rather than received\_at\_utc.

\- Exclude duplicate events and invalid or unenrolled activity.



\### 4.2 Active Days

\- Definition: Number of distinct calendar days on which a learner generated valid activity in a course during a week.

\- Source: activity\_events.

\- Calculation: COUNT(DISTINCT activity date).

\- Maximum value: 7 days.



\### 4.3 Valid Event Count

\- Definition: Number of accepted activity events after validation and duplicate handling.

\- Source: activity\_events.

\- Calculation: COUNT(valid event\_id).



\### 4.4 Total Engagement Minutes

\- Definition: Total time spent on valid learning activities.

\- Source: activity\_events.

\- Calculation:



&#x20; Engagement Minutes = SUM(duration\_seconds) / 60



\- Duplicate events must not increase engagement time.



\### 4.5 Unique Content Items

\- Definition: Number of distinct content items accessed by a learner during a reporting week.

\- Source: activity\_events.

\- Calculation: COUNT(DISTINCT content\_item\_id).

\- Ignore NULL content item references.



\## 5. Assessment Metrics



\### 5.1 Total Assessments

\- Definition: Total number of assessment records.

\- Source: assessments.

\- Calculation: COUNT(DISTINCT assessment\_id).



\### 5.2 Total Attempts

\- Definition: Total recorded assessment attempts.

\- Source: attempts.

\- Calculation: COUNT(DISTINCT attempt\_id).



\### 5.3 Graded Attempts

\- Definition: Attempts that have completed grading.

\- Source: attempts.

\- Calculation: COUNT(attempt\_id) WHERE attempt\_status = 'GRADED'.



\### 5.4 Assessment Pass Rate

\- Definition: Percentage of graded attempts that passed.

\- Source: attempts.

\- Calculation:



&#x20; Pass Rate = (Passed Graded Attempts / Total Graded Attempts) \* 100



\- Only graded attempts are included in the denominator.



\### 5.5 Average Assessment Score

\- Definition: Average score across graded attempts.

\- Source: attempts.

\- Calculation: AVG(score) WHERE attempt\_status = 'GRADED'.



\- Scores must be interpreted against the assessment maximum score.



\## 6. Cohort Metrics



\### 6.1 Cohort Enrollment Count

\- Definition: Number of enrollments associated with a cohort and course.

\- Source: enrollments.

\- Calculation: COUNT(DISTINCT enrollment\_id).



\### 6.2 Cohort Active Count

\- Definition: Number of enrolled learners with at least one valid activity event during the reporting window.

\- Source: enrollments and activity\_events.

\- Calculation: COUNT(DISTINCT learner\_id) with valid activity in the window.



\### 6.3 Cohort Completed Count

\- Definition: Number of cohort enrollments with a completed course outcome.

\- Source: enrollments and course\_outcomes.

\- Calculation: COUNT(DISTINCT enrollment\_id) WHERE outcome\_status = 'COMPLETED'.



\### 6.4 Cohort Completion Rate

\- Definition: Percentage of cohort enrollments completed during the reporting period.



&#x20; Completion Rate = (Completed Count / Enrolled Count) \* 100



\### 6.5 Average Cohort Engagement

\- Definition: Average valid engagement minutes per active learner during the reporting window.



&#x20; Average Engagement = Total Valid Engagement Minutes / Active Learner Count



\## 7. Anomaly Metrics



\### 7.1 Total Detected Anomalies

\- Definition: Total anomaly records identified by the validation process.

\- Source: anomaly\_records.

\- Calculation: COUNT(anomaly\_id).



\### 7.2 Anomalies by Type

\- Definition: Number of detected anomalies grouped by issue type.

\- Source: anomaly\_records.

\- Calculation: COUNT(anomaly\_id) GROUP BY issue\_type.



\### 7.3 Open Anomalies

\- Definition: Anomalies that are awaiting review or resolution.

\- Source: anomaly\_records.

\- Calculation: COUNT(anomaly\_id) WHERE detection\_status = 'OPEN'.



\### 7.4 Resolved Anomalies

\- Definition: Anomalies that have been successfully resolved.

\- Source: anomaly\_records.

\- Calculation: COUNT(anomaly\_id) WHERE detection\_status = 'RESOLVED'.



\### 7.5 Anomaly Detection Evaluation

\- Definition: Comparison of detected anomaly results with the expected ground-truth labels.

\- Sources: anomaly\_records and ground\_truth.



\- True Positive (TP): An actual anomaly correctly detected.

\- False Positive (FP): A normal record incorrectly detected as an anomaly.

\- False Negative (FN): An actual anomaly that was not detected.

\- True Negative (TN): A normal record correctly identified as normal.



Precision = TP / (TP + FP)



Recall = TP / (TP + FN)



F1 Score = 2 \* (Precision \* Recall) / (Precision + Recall)



If a denominator is zero, report the metric as unavailable rather than dividing by zero.



Ground-truth labels must never be used as input features for anomaly detection.



\## 8. Reporting Rules



1\. All reporting periods must use consistent start and end dates.

2\. Activity calculations must use event\_time\_utc.

3\. received\_at\_utc must be used for ingestion and synchronization analysis.

4\. Duplicate events must not inflate engagement metrics.

5\. Activity without a valid enrollment must be excluded from normal learner engagement.

6\. Timezone anomalies must be identified and corrected or excluded from affected time-based analytics.

7\. Historical records must be retained for traceability.

8\. NULL values must be handled consistently.

9\. Metrics must be recalculated from validated source records.

10\. Every metric calculation should record its calculation timestamp.



\## 9. Data Sources



| Metric Category | Source Tables |

|---|---|

| Learner Metrics | learners |

| Course Metrics | courses, enrollments, course\_outcomes |

| Engagement Metrics | activity\_events, weekly\_engagement\_metrics |

| Assessment Metrics | assessments, attempts |

| Cohort Metrics | cohorts, cohort\_learners, enrollments, cohort\_metrics |

| Anomaly Metrics | anomaly\_records, ground\_truth |

| Processing Monitoring | processing\_runs |



\## 10. Conclusion



These metric definitions establish a consistent method for measuring learner participation, course progress, assessment performance, cohort performance and data quality.



All dashboard metrics must be calculated from validated database records and must follow the documented business rules.
