# Third-Party Notices

AttendX AI is independently implemented. No code, assets, fonts, screenshots, datasets or credentials
from the SnapClass reference repositories are included; both reference repositories report no licence
and are therefore all-rights-reserved research material only.

The project depends on open-source libraries. The table is a summary for engineering awareness and is
not a legal opinion. Review each project's current licence and notices before distribution.

## Backend (Python)

| Package | Licence | Use |
|---|---|---|
| FastAPI | MIT | HTTP API framework |
| Starlette | BSD-3-Clause | ASGI toolkit underlying FastAPI |
| Pydantic / pydantic-settings | MIT | Validation and configuration |
| SQLAlchemy | MIT | ORM and SQL toolkit |
| Alembic | MIT | Database migrations |
| Uvicorn | BSD-3-Clause | ASGI server |
| websockets | BSD-3-Clause | Installed for future/live use; current UI uses polling |
| argon2-cffi / argon2-cffi-bindings | MIT / MIT | Argon2id password and PIN hashing |
| python-multipart | Apache-2.0 | Multipart uploads |
| email-validator | Unlicense (public domain) | Email syntax validation |
| psycopg 3 | LGPL-3.0 (with exceptions) | PostgreSQL driver (production) |
| pytest / pytest-cov / httpx | MIT / MIT / BSD-3-Clause | Development and testing |

## Frontend (Node)

| Package | Licence | Use |
|---|---|---|
| Next.js | MIT | React framework / App Router |
| React / React DOM | MIT | UI runtime |
| TypeScript | Apache-2.0 | Type checking |
| Tailwind CSS / @tailwindcss/postcss | MIT | Styling |
| lucide-react | ISC | Icons |
| qrcode | MIT | QR rendering |
| jsqr | Apache-2.0 | In-browser QR decoding |
| recharts | MIT | Installed for charts; current build uses lightweight CSS bars in core views |
| clsx | MIT | Class name composition |

## Assets and data

- No third-party fonts are bundled; the UI uses the system font stack with an Inter preference.
- No stock imagery is included. Illustrations are CSS/HTML.
- No biometric model weights or datasets are bundled.
- Test/demo identities use the synthetic `@attendx.dev` domain; no real student or faculty data is
  present.

## Verification providers

Face and liveness are optional external services selected by the institution. Their licences, data
processing terms, retention and deletion obligations are separate contractual matters. This
repository defines only an HTTP contract and an unconfigured state.
