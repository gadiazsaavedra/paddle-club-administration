// Autocompletado para selects de productos y jugadores usando datalist
function agregarAutocomplete() {
  // Para selects de productos
  document.querySelectorAll('input[list][name$="-producto"]').forEach(function(input) {
    input.setAttribute('autocomplete', 'on');
  });
  // Para selects de jugadores (si existiera)
  document.querySelectorAll('input[list][name="jugador"]').forEach(function(input) {
    input.setAttribute('autocomplete', 'on');
  });
}
document.addEventListener('DOMContentLoaded', agregarAutocomplete);
