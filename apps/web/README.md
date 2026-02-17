# Awaqi Web Frontend

This is the Next.js frontend for the Awaqi Ethio-Revenue-Bot.

## Project Structure

### Routes

- **`/`**: Landing Page - Public facing introduction and features.
- **`/[locale]/login`**: Authentication page.
- **`/[locale]/chat`**: **Main User Interface** - The chat interface for interacting with the bot.
  - **`/[locale]/chat/history`**: View past conversation history.
  - **`/[locale]/chat/settings`**: User settings.
- **`/[locale]/(admin)/admin`**: Admin implementation for managing the system.

### Key Directories

- `app/`: Next.js App Router structure.
- `components/`: React components.
  - `components/chat/`: Chat-specific components.
  - `components/landing/`: Landing page components.
  - `components/layout/`: Shared layout components (Sidebar, Navbar).
- `messages/`: Internationalization (i18n) strings.

## getting started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) with your browser.
