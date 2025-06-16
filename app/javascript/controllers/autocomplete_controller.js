// Path: app/javascript/controllers/autocomplete_controller.js

import { Controller } from "@hotwired/stimulus"

// Connects to data-controller="autocomplete"
export default class extends Controller {
  static targets = [ "input", "results", "hidden" ]
  static values = { url: String }

  search() {
    const query = this.inputTarget.value;
    if (query.length > 2) {
      fetch(`${this.urlValue}?query=${encodeURIComponent(query)}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
          }
          return response.json();
        })
        .then(data => {
          this.resultsTarget.innerHTML = "";
          if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
              let li = document.createElement("li");
              li.textContent = item.name;
              li.dataset.playerId = item.id; // Store ID on the element
              li.addEventListener("click", this.selectPlayer.bind(this));
              this.resultsTarget.appendChild(li);
            });
          }
        })
        .catch(error => {
          this.resultsTarget.innerHTML = "<li class='error'>Error loading results</li>";
        });
    } else {
      this.resultsTarget.innerHTML = "";
    }
  }

  selectPlayer(event) {
    const selectedPlayerName = event.target.textContent;
    const selectedPlayerId = event.target.dataset.playerId;

    // Update the value of BOTH the visible and hidden inputs
    this.inputTarget.value = selectedPlayerName;  // Set visible input to player's name
    this.hiddenTarget.value = selectedPlayerId; // Set hidden input to player's ID

    this.resultsTarget.innerHTML = ""; // Clear results
  }
}
