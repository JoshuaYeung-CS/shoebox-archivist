# Disclosure

## Principal functionality developed for this hackathon

Everything in this package was written new for the UGREEN Hackathon 2026 on AI NAS: the workflow in SKILL.md, the date evidence method and date stamp reading rules, the Archive Plan review format, the story rules, the run ledger with resume and undo, the state and edge case handling, and the privacy design. No earlier Skill or submission material was reused.

This is an independent Skill. It is not an official UGREEN Skill.

## Third-party components

| Component | Source | License | How it is used |
|---|---|---|---|
| Uliya Skill Kit 0.7.3 (English), the UGOS Skill Creation Tool | UGREEN Hackathon Starter Kit page, file uliya-skill-kit-0.7.3-en.zip, SHA-256 cf557e5a022e4297892f39768132855154232efdedeb726b2845450ccd70e1b3 | No license file is included in the kit archive. Its use is governed by the Hackathon Official Rules and the UGREEN agreements linked from the Starter Kit page: the UGREEN SkillHub User Agreement, the UGREEN SkillHub Privacy Policy, and the UGREEN SkillHub Content Submission and Publication Standards. | Development tooling only: the Uliya Skill Development Standard, the capability catalog (version 2.0.0) used to confirm every CLI and expert mapping, and the static checker used to validate this package. No kit file is included in this package. |

No open source libraries, external APIs, external services, models, datasets, images or fonts are included in or required by this package. At run time the Skill uses only the registered UGOS experts (file-agent, photo-agent, document-agent, knowledge-agent) and the NAS default on-device models they use.

## External services and data flows

None. All reads and writes happen on the NAS through the registered experts; see [privacy and permissions](privacy-and-permissions.md).

## License of this Skill

MIT License. Copyright (c) 2026 Joshua Yeung.

## AI tools used and their principal uses

[JOSHUA TO FILL: AI tools used in development]
