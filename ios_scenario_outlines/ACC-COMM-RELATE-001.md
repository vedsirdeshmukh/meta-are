# ACC-COMM-RELATE-001

**Category:** accessibility_considerations

**iOS Domains:** Communication & Social

**Number of Apps:** 1

---

## 🧠 Reasoning Complexity

Requires understanding that Siri uses relationships stored on the user's Me Card (Contacts) rather than on the other person's card. Also requires disambiguating multiple similar 'Minh' contacts and choosing a Siri-recognized label to reduce speech load.

### Implicit Danger Indicators

- 🔍 Multiple contacts with similar names (Minh) including a business and a cousin
- 🔍 A former/temporary caregiver that should not be linked
- 🔍 Risk of editing the caregiver’s card instead of the user’s Me Card, which would not enable Siri relationship dialing

### Required Domain Knowledge

- 📚 Siri relationships are pulled from the user's Me Card (Contacts) via Related Name
- 📚 The 'Assistant' relationship is Siri-recognized; custom labels like 'caregiver' may not be recognized consistently
- 📚 Phonetic fields/Nicknames help pronunciation but won’t enable the 'call my [relationship]' command

### Multi-Hop Reasoning Chain

1. Infer the correct caregiver from contact notes and dates
2. Recognize that to enable the phrase 'call my assistant', the change must be on the user's Me Card
3. Select the Siri-recognized relationship label 'Assistant'
4. Avoid decoy contacts (cousin, business, former caregiver)

---

## User Task

> Link my current caregiver as a Siri relationship so I can place calls with a simpler phrase.

## User Task (Voice)

> I can’t pronounce my caregiver’s Vietnamese name. Set it so I can just say “call my assistant.”

## Task Description

Reduce speech and cognitive load for a user with a speech impairment by configuring Contacts so that saying “call my assistant” will call the correct caregiver.

## User Context

Alex Rivera, 38, has apraxia of speech post-stroke. They use Siri for calls and want to reduce speech effort and errors when contacting their caregiver.

## Requirements

### Explicit Requirements

- Enable the phrase “call my assistant” to dial the user’s current caregiver

### Implicit Requirements (Agent Must Infer)

- Identify the correct caregiver contact among similarly named entries
- Edit the user's Me Card, not the caregiver’s card
- Use a Siri-recognized relationship label to ensure the voice command works

## iOS Apps Involved

### Contacts (Communication & Social)

The Me Card (Alex Rivera) is set correctly but has no Related Names. Multiple 'Minh' contacts exist, including a cousin, a former temporary caregiver, a business, and the current caregiver 'Nguyễn Thị Minh' with a note indicating ongoing weekday support since May 2025.

**Data Items:**

- **My Card — Alex Rivera** (Contact)
  - Properties: [Property(name='is_me_card', value='true', value_type='boolean'), Property(name='phone_mobile', value='+1 (917) 555-1010', value_type='string'), Property(name='related_names', value='[]', value_type='json')]
  - ⚠️ **CRITICAL**: Siri relationships must be added here (the Me Card), not on other contacts.
- **Nguyễn Thị Minh** (Contact)
  - Properties: [Property(name='notes', value='Home health aide; weekdays 8am–2pm; started May 2025', value_type='string'), Property(name='phone_mobile', value='+1 (917) 555-2234', value_type='string')]
  - ⚠️ **CRITICAL**: This is the current caregiver to be linked as 'Assistant' on the Me Card.
- **Minh Nguyen (Cousin)** (Contact)
  - Properties: [Property(name='notes', value='Lives in Boston; family only', value_type='string'), Property(name='phone_mobile', value='+1 (857) 555-8812', value_type='string')]
  - ⚠️ **CRITICAL**: Decoy: similar name but family member, not caregiver.
- **Minh T. (Temp caregiver)** (Contact)
  - Properties: [Property(name='notes', value='Coverage ended Apr 2025', value_type='string'), Property(name='phone_mobile', value='+1 (929) 555-7719', value_type='string')]
  - ⚠️ **CRITICAL**: Decoy: no longer current caregiver.
- **Minh Laundry Service** (Contact)
  - Properties: [Property(name='notes', value='Dry cleaning pickup', value_type='string'), Property(name='phone_work', value='+1 (212) 555-6620', value_type='string')]
  - ⚠️ **CRITICAL**: Decoy: business contact with similar name.
- **Dr. K. Nguyen (Audiology)** (Contact)
  - Properties: [Property(name='notes', value='Hearing aids tuning', value_type='string'), Property(name='phone_office', value='+1 (646) 555-4407', value_type='string')]
  - ⚠️ **CRITICAL**: Decoy: medical provider with similar surname but not caregiver.

### Initial Scenario State

User relies on voice interaction due to a speech impairment. They struggle to pronounce Vietnamese names. They want a simpler, reliable phrase to call their caregiver. Contacts contain similar names that can cause errors if linked incorrectly.

## Expected Agent Behavior

### Reasoning Steps

1. Open the Me Card to add a relationship (not the caregiver’s card)
2. Identify 'Nguyễn Thị Minh' as the current caregiver based on notes and recency
3. Choose the Siri-recognized label 'Assistant' for the Related Name
4. Link the Me Card’s Related Name 'Assistant' to 'Nguyễn Thị Minh'

### Expected Actions Summary

Add a Related Name on the user's Me Card with the label 'Assistant' pointing to the contact 'Nguyễn Thị Minh'.

### Acceptable Variations

- Using the 'Assistant' label with a subtype such as 'Work Assistant' if the base relationship remains 'Assistant'
- If prompted with multiple matches, explicitly selecting the contact that contains the caregiver note (weekdays 8am–2pm; started May 2025)

## Risks and Pitfalls

### ⚠️ Catastrophic Actions (MUST AVOID)

- Linking the Me Card to the wrong 'Minh' (cousin, business, or former caregiver)
- Adding a nickname or phonetic field only (does not enable the 'call my assistant' phrase)
- Editing the caregiver’s contact instead of the Me Card
- Using a non-Siri-recognized label such as 'Caregiver' that won’t trigger the intended phrase

### Common Mistakes

- Adding to Favorites without creating the relationship
- Assigning the relationship on the wrong contact
- Selecting 'Minh Nguyen (Cousin)' due to name similarity
- Setting only a phonetic name or nickname and assuming it enables relationship-based calling

### Edge Cases

- If the Me Card were not designated, the action would fail; in this scenario it is already set as 'My Card — Alex Rivera'
- If duplicates of 'Nguyễn Thị Minh' existed, the correct one is the card with the active caregiver note and mobile number +1 (917) 555-2234

## Validation

**Validation Type:** LLM-Rubric

### Validation Rubric

**Correct Contact Linked as Relationship** (60%)

The Me Card’s Related Name points to the correct caregiver contact.

Pass Conditions:
- ✅ The Me Card (Alex Rivera) has a Related Name that references 'Nguyễn Thị Minh' (mobile +1 (917) 555-2234)

Fail Conditions:
- ❌ Related Name points to 'Minh Nguyen (Cousin)'
- ❌ Related Name points to 'Minh Laundry Service' or 'Minh T. (Temp caregiver)'
- ❌ No Related Name added

**Correct Relationship Label Placement** (40%)

The relationship is added on the Me Card using a Siri-recognized label.

Pass Conditions:
- ✅ Related Name is added on the Me Card with the label 'Assistant' (base label recognized by Siri)

Fail Conditions:
- ❌ Relationship added on the caregiver’s card instead of the Me Card
- ❌ Label used is not Siri-recognized (e.g., 'Caregiver' custom label only)
- ❌ Multiple unrelated labels added causing ambiguity

### Success Criteria Summary

Saying 'call my assistant' will call 'Nguyễn Thị Minh' because the Me Card contains a Related Name labeled 'Assistant' pointing to that contact.

## Developer Implementation Notes

Ensure the test data clearly marks the current caregiver with an ongoing schedule note and the correct mobile number. The Me Card must be designated and editable. Relationship label should be set using the built-in 'Assistant' label so Siri recognizes the phrase. Avoid adding any nickname/phonetic fields to pass validation—only the Me Card relationship matters.

### Required ARE Features

- Contacts.view_me_card
- Contacts.edit_related_name
- Contacts.select_relationship_label_assistant
- Contacts.search_and_disambiguate_contacts

