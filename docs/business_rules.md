# Learning Analytics Platform - Business Rules



## 1. Enrollment Rules

- Only valid learner-course enrollments can generate normal course activity.

- Enrollment status changes must be recorded in enrollment history.

- Withdrawn learners cannot generate normal activity after withdrawal.

- Suspended learners retain their historical activity.



## 2. Activity Rules

- Activity events must reference valid learners and courses.

- Normal enrolled activity must reference a valid enrollment.

- Content activity must reference content belonging to the same course.

- Duplicate events must be identified using source event references.

- Offline events may arrive later than their event time.

- Late events must retain their original event timestamp.



## 3. Assessment Rules

- Attempts must belong to the correct learner, enrollment and assessment.

- A learner can make a maximum of three attempts.

- Only graded attempts have scores and pass/fail results.

- Passing is determined using the assessment passing score.



## 4. Course Completion Rules

- Course completion must follow the effective completion rule.

- Required assessments must satisfy their passing requirements.

- Content completion must satisfy the configured minimum percentage.

- Completion before required conditions are met must be flagged.

- Completion outcomes must be derived from source records.



## 5. Engagement Rules

- Weekly active learners are learners with at least one valid activity event in a week.

- Duplicate events must not inflate engagement.

- Engagement must be calculated using event time, not received time.

- Cohort metrics must use consistent reporting periods.



## 6. Anomaly Rules

- Duplicate activity.

- Activity without enrollment.

- Premature course completion.

- Timezone misalignment.



All anomalies must retain their ground-truth labels for validation.
