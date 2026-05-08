# Javaab White-Label Chat Widget

React/Vite frontend that B2B clients (schools, coaching institutes) embed in their platforms. Connects to the Javaab backend API for curriculum-aligned AI responses.

## Features

- Curriculum-aligned AI chat (NCERT + GSEB, classes 6–12)
- Multi-language responses (English, Hindi, Gujarati)
- Image upload for handwritten question solving
- Conversation history with bookmarks
- Question paper generator (`/admin/papers`)
- DPP worksheet builder (`/admin/worksheets`)
- JWT-based session auth

## Development

```bash
npm install
npm run dev        # starts at http://localhost:5173
npm run build      # production build
npm run typecheck  # TypeScript check only
```

## Environment Variables

```bash
# .env.local
VITE_API_URL=http://localhost:8000   # backend URL
```

## Key Routes

| Route | Description |
|-------|-------------|
| `/` | Login / entry point |
| `/onboarding` | First-run setup (board, class, language) |
| `/chat` | Main AI chat interface |
| `/settings` | Profile and study settings |
| `/admin/papers` | Question paper generator |
| `/admin/papers/new` | Create new paper |
| `/admin/worksheets` | DPP worksheet builder |
| `/admin/worksheets/new` | Create new worksheet |

## Tech Stack

- React 18, TypeScript (strict), Vite
- TailwindCSS + shadcn/ui components
- React Router v6
- Lucide icons, Sonner toasts
