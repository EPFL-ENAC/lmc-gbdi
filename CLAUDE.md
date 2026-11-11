# lmc-gbdi

## Dev servers and worktrees

Every branch has its own git worktree, tmux session and agent. The session is
`lmc-gbdi/<branch>` and its panes are `agent`, `backend`, `frontend`, `shell`.

- Ports are per worktree and live in `.env.worktree`, which every pane exports.
  Never hardcode a port, read `BACKEND_PORT`, `FRONTEND_PORT` from the environment.
- The dev servers are already running in their own panes. Do not start them
  again. Read `.wt-logs/*.log` to see what they are doing, the sandbox cannot
  reach the tmux socket.
- `wtx curl <family> [path] [curl args]` is how you reach them. It fills in this
  worktree's port and never prompts, whatever the method: `wtx curl backend
  /api/health`. Plain curl to localhost works for a GET and prompts past that.
- Work on this branch only. Never push `dev` and `main`. When the work is ready, say
  so and a human runs `wtx land <branch>` from the main checkout.
- A pre-push hook enforces this. If it refuses a push, that is the design, not a
  bug to work around.

### Directories outside this repo

- `books` at `../books`, access `read`.
- `lmc-openbdf` at `../lmc-openbdf`, access `pair`.

A `read` directory is yours to read as much as you like, with no prompt, and you
may never write in it. To change one, ask for a paired worktree instead: a human
runs `wtx go <branch> --with <name>=<branch>`, and the change lands through that
repo's own pull request.

