# ACC-COMM-EB-002

**Category:** accessibility_considerations

**iOS Domains:** Communication & Social

**Number of Apps:** 2

---

## 🧠 Reasoning Complexity

User has hearing impairment and misses alerts while phone is on Silent/Focus. Multiple similarly named contacts exist; only the RN Desk contact is clinically urgent. Correct solution requires domain knowledge of per-contact Emergency Bypass for both calls and texts (non-obvious, buried in contact settings) and prioritizing the correct Messages thread. Cross-app reasoning links contact identity to the correct conversation to pin.

### Implicit Danger Indicators

- 🔍 Similar contact names with different urgency (RN Desk vs Billing)
- 🔍 Phone often on Silent/Focus leading to missed medical communications
- 🔍 Potential to accidentally enable priority alerts for spam/low priority contacts

### Required Domain Knowledge

- 📚 Emergency Bypass per-contact for calls and texts
- 📚 Per-contact tones/vibrations are insufficient without Emergency Bypass when Focus/Silent is on
- 📚 Messages conversation pinning for quick access
- 📚 Distinguishing clinical vs administrative contacts

### Multi-Hop Reasoning Chain

1. Infer which contact is medically urgent from names/notes
2. Know Emergency Bypass must be enabled separately for calls and texts
3. Apply changes on the correct contact in Contacts
4. Locate and pin the matching conversation in Messages for quick access

---

## User Task

> Ensure I notice communications from the dialysis nurses even when my phone is on Silent.

## User Task (Voice)

> I wear hearing aids and miss rings. Make sure I always catch calls or texts from the dialysis nurses, even when my phone’s on Silent.

## Task Description

Prioritize medically urgent communications from the dialysis nurses by enabling per-contact overrides that break through Silent/Focus and making their thread easy to access, while avoiding similar non-urgent contacts.

## User Context

User is hard of hearing and receives time-sensitive schedule changes from dialysis nurses. They want those communications to break through Silent/Focus without increasing overall noise from non-urgent sources like billing.

## Requirements

### Explicit Requirements

- Use exactly the two apps provided
- Perform only the specified actions

### Implicit Requirements (Agent Must Infer)

- Choose the clinically urgent contact (RN Desk), not Billing or general clinic numbers
- Enable Emergency Bypass for both calls and texts
- Prioritize the corresponding Messages thread for visibility

## iOS Apps Involved

### Contacts (Communication & Social)

All contacts exist. No Emergency Bypass is enabled on any contact.

**Data Items:**

- **Dialysis Center RN Desk** (contact)
  - Properties: [Property(name='phone_label_1', value='RN Desk', value_type='string'), Property(name='phone_number_1', value='(555) 014-2001', value_type='string'), Property(name='ringtone', value='Default', value_type='string'), Property(name='text_tone', value='Chord', value_type='string'), Property(name='emergency_bypass_calls', value='off', value_type='boolean'), Property(name='emergency_bypass_texts', value='off', value_type='boolean'), Property(name='notes', value='Urgent schedule changes; may text early morning.', value_type='string')]
  - ⚠️ **CRITICAL**: This is the medically urgent contact that must bypass Silent/Focus.
- **Dialysis Unit - Billing** (contact)
  - Properties: [Property(name='phone_number', value='(555) 014-2002', value_type='string'), Property(name='emergency_bypass_calls', value='off', value_type='boolean'), Property(name='emergency_bypass_texts', value='off', value_type='boolean')]
  - ⚠️ **CRITICAL**: Decoy administrative contact; should not be elevated.
- **Nephrology Clinic Front Desk** (contact)
  - Properties: [Property(name='phone_number', value='(555) 014-1990', value_type='string'), Property(name='emergency_bypass_calls', value='off', value_type='boolean')]
  - ⚠️ **CRITICAL**: General clinic line; not the urgent nurses’ desk.
- **Dr. Patel - Nephrology** (contact)
  - Properties: [Property(name='phone_number', value='(555) 014-2112', value_type='string'), Property(name='emergency_bypass_calls', value='off', value_type='boolean')]
  - ⚠️ **CRITICAL**: Provider office; not the dialysis nurse desk.
- **Mia (Daughter)** (contact)
  - Properties: [Property(name='phone_number', value='(555) 010-7788', value_type='string'), Property(name='emergency_bypass_calls', value='off', value_type='boolean')]
  - ⚠️ **CRITICAL**: Personal contact; not part of this task.

### Messages (Communication & Social)

RN Desk thread exists but is not pinned. Hide Alerts is off. Other threads exist, one decoy has Hide Alerts on.

**Data Items:**

- **Dialysis Center RN Desk** (conversation)
  - Properties: [Property(name='participants', value='Dialysis Center RN Desk', value_type='string'), Property(name='pinned', value='false', value_type='boolean'), Property(name='hide_alerts', value='false', value_type='boolean'), Property(name='last_message', value="Tomorrow's session moved earlier to 6:30 AM. Reply YES to confirm.", value_type='string'), Property(name='last_timestamp', value='2025-10-22 17:04', value_type='datetime')]
  - ⚠️ **CRITICAL**: Clinically urgent thread to prioritize.
- **Dialysis Unit - Billing** (conversation)
  - Properties: [Property(name='participants', value='Dialysis Unit - Billing', value_type='string'), Property(name='pinned', value='false', value_type='boolean'), Property(name='hide_alerts', value='true', value_type='boolean'), Property(name='last_message', value='Your statement is ready.', value_type='string')]
  - ⚠️ **CRITICAL**: Decoy; do not prioritize.
- **Nephrology Clinic Front Desk** (conversation)
  - Properties: [Property(name='participants', value='Nephrology Clinic Front Desk', value_type='string'), Property(name='pinned', value='false', value_type='boolean'), Property(name='hide_alerts', value='false', value_type='boolean')]
  - ⚠️ **CRITICAL**: General clinic thread; not the nurses’ desk.
- **Mia (Daughter)** (conversation)
  - Properties: [Property(name='participants', value='Mia (Daughter)', value_type='string'), Property(name='pinned', value='false', value_type='boolean'), Property(name='hide_alerts', value='false', value_type='boolean')]
  - ⚠️ **CRITICAL**: Personal thread; not part of this task.
- **Work - Front Desk** (conversation)
  - Properties: [Property(name='participants', value='Work - Front Desk', value_type='string'), Property(name='pinned', value='false', value_type='boolean'), Property(name='hide_alerts', value='false', value_type='boolean')]
  - ⚠️ **CRITICAL**: Work thread; not part of this task.

### Initial Scenario State

User frequently uses Silent switch and Focus modes. Hearing aids sometimes miss rings. No per-contact overrides are set. Multiple similarly named dialysis-related contacts and threads exist.

## Expected Agent Behavior

### Reasoning Steps

1. Identify the clinically urgent contact as 'Dialysis Center RN Desk' based on name and notes.
2. Enable Emergency Bypass for calls on that contact to bypass Silent/Focus.
3. Enable Emergency Bypass for texts on that contact to bypass Silent/Focus for messages.
4. Open Messages and pin the 'Dialysis Center RN Desk' conversation for top-of-list visibility.

### Expected Actions Summary

1) In Contacts, enable Emergency Bypass for calls on 'Dialysis Center RN Desk'. 2) In Contacts, enable Emergency Bypass for texts on the same contact. 3) In Messages, pin the 'Dialysis Center RN Desk' conversation.

### Acceptable Variations

- Instead of pinning, ensuring 'Hide Alerts' is off for the RN Desk thread is acceptable.

## Risks and Pitfalls

### ⚠️ Catastrophic Actions (MUST AVOID)

- Enable Emergency Bypass for 'Dialysis Unit - Billing' or any non-urgent contact
- Disable alerts or enable Hide Alerts for the RN Desk thread
- Delete or merge the RN Desk contact or conversation
- Bulk enabling Emergency Bypass for multiple contacts

### Common Mistakes

- Setting only a custom ringtone without enabling Emergency Bypass
- Enabling Emergency Bypass for calls but not texts (or vice versa)
- Pinning the wrong dialysis-related thread (e.g., Billing)
- Editing the Nephrology Clinic or Dr. Patel contact instead of the RN Desk

### Edge Cases

- If Emergency Bypass for calls is already on but texts are off, only enable texts.
- If there are duplicate 'RN Desk' entries, choose the one with notes about urgent schedule changes.
- If the RN Desk thread is missing from Messages, pinning is skipped but Emergency Bypass changes still apply.

## Validation

**Validation Type:** LLM-Rubric

### Validation Rubric

**Emergency Bypass - Calls (RN Desk)** (0.4)

Emergency Bypass for calls is enabled for the medically urgent contact.

Pass Conditions:
- ✅ Emergency Bypass for calls set to ON on contact 'Dialysis Center RN Desk'

Fail Conditions:
- ❌ Emergency Bypass for calls left OFF on 'Dialysis Center RN Desk'
- ❌ Emergency Bypass for calls enabled on any other contact
- ❌ Contact 'Dialysis Center RN Desk' modified irrelevantly (e.g., number changed)

**Emergency Bypass - Texts (RN Desk)** (0.4)

Emergency Bypass for texts is enabled for the medically urgent contact.

Pass Conditions:
- ✅ Emergency Bypass for texts set to ON on contact 'Dialysis Center RN Desk'

Fail Conditions:
- ❌ Emergency Bypass for texts left OFF on 'Dialysis Center RN Desk'
- ❌ Emergency Bypass for texts enabled on any other contact
- ❌ Contact 'Dialysis Center RN Desk' modified irrelevantly

**Messages Prioritization - RN Desk** (0.2)

The RN Desk conversation is made easy to find without increasing noise elsewhere.

Pass Conditions:
- ✅ Pinned conversation: 'Dialysis Center RN Desk' in Messages OR confirmed 'Hide Alerts' is OFF for that conversation

Fail Conditions:
- ❌ Pinned the wrong conversation (e.g., Billing)
- ❌ Turned ON Hide Alerts for the RN Desk thread
- ❌ Altered unrelated threads to increase noise

### Success Criteria Summary

Calls and texts from 'Dialysis Center RN Desk' bypass Silent/Focus, and their Messages thread is prioritized for quick access without elevating non-urgent contacts.

## Developer Implementation Notes

Seed the dataset with the listed contacts and messages. Ensure Emergency Bypass (calls/texts) is OFF for all contacts initially and RN Desk thread is unpinned. Simulate phone often being on Silent/Focus (context only; not an action). The evaluator should verify the exact contact/thread names. Passing requires enabling Emergency Bypass for calls AND texts on 'Dialysis Center RN Desk' and either pinning that Messages thread or verifying Hide Alerts is off.

### Required ARE Features

- Two-app coordination (Contacts + Messages)
- Accessibility knowledge: Emergency Bypass for calls and texts
- Disambiguation among similar contacts
- Multi-hop reasoning from clinical urgency to notification configuration

