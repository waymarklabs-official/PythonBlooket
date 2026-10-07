/** Host screens (teacher's view of a hosted game). PLACEHOLDER - replaced by the host UI work. */
import { el } from "./ui.js";

export function renderHost(env) {
  env.show(
    el("div", { class: "screen" }, env.backButton("Back", () => env.goHome()), el("h1", { text: "Host a game" }), el("p", { text: "Coming soon." }))
  );
}
