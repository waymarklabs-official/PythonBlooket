/** Player screens (joining and playing a hosted game). PLACEHOLDER - replaced by the player UI work. */
import { el } from "./ui.js";

export function renderJoin(env, { code } = {}) {
  env.show(
    el("div", { class: "screen" }, env.backButton("Back", () => env.goHome()), el("h1", { text: "Join a game" }), el("p", { text: code ? `Code ${code} - coming soon.` : "Coming soon." }))
  );
}
