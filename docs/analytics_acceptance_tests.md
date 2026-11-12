\# Analytics Acceptance Test Cases



\## 1. Learner Metrics

\- Verify total learner count using distinct learner IDs.

\- Verify active learner count using ACTIVE status.

\- Verify inactive learner count using INACTIVE status.

\- Verify suspended learner count using SUSPENDED status.



\## 2. Course Metrics

\- Verify total course count.

\- Verify published course count.

\- Verify enrollment count grouped by course.

\- Verify completion rate using the documented eligible enrollment population.



\## 3. Engagement Metrics

\- Count unique learners with at least one valid event per week.

\- Exclude duplicate events from engagement calculations.

\- Exclude activity without valid enrollment.

\- Calculate engagement using event\_time\_utc.

\- Calculate active days using distinct activity dates.

\- Calculate engagement minutes using duration\_seconds / 60.

\- Ignore NULL content\_item\_id values when counting unique content items.



\## 4. Assessment Metrics

\- Verify total assessment count.

\- Verify total attempt count.

\- Count only GRADED attempts in graded-attempt metrics.

\- Calculate pass rate using passed graded attempts divided by all graded attempts.

\- Calculate average score using graded attempts only.

\- Verify that no enrollment has more than three attempts per assessment.



\## 5. Course Completion

\- Apply the effective completion rule.

\- Verify required assessment passing conditions.

\- Verify minimum content completion percentage.

\- Flag premature completion events.

\- Derive outcomes from source records.



\## 6. Cohort Metrics

\- Verify enrollment count grouped by cohort and course.

\- Count unique active learners during the reporting window.

\- Calculate completed enrollment count.

\- Calculate completion rate using a consistent reporting population.

\- Calculate average valid engagement minutes per active learner.



\## 7. Anomaly Handling

\- Identify duplicate events.

\- Identify activity without enrollment.

\- Identify premature completion.

\- Identify timezone misalignment.

\- Compare detected anomalies against ground truth.

\- Calculate precision, recall and F1 score.

\- Ensure ground truth is not used as a detection input.



\## 8. Data Integrity

\- Verify all metric queries use valid source records.

\- Verify duplicate events do not inflate metrics.

\- Verify reporting periods use consistent start and end dates.

\- Verify NULL values are handled consistently.

\- Verify historical records are retained.

\- Record the calculation timestamp for generated metrics.
