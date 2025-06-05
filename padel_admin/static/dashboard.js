// Funciones para mejorar la experiencia de usuario en el dashboard

// Inicialización de componentes
document.addEventListener('DOMContentLoaded', function() {
  // Inicializar tooltips
  initTooltips();
  
  // Añadir animaciones de entrada
  addEntryAnimations();
  
  // Inicializar validación de formularios
  initFormValidation();
  
  // Inicializar notificaciones
  initNotifications();
});

// Inicializar tooltips personalizados
function initTooltips() {
  const tooltipElements = document.querySelectorAll('[data-tooltip]');
  
  tooltipElements.forEach(element => {
    element.addEventListener('mouseenter', function() {
      const tooltipText = this.getAttribute('data-tooltip');
      const tooltip = document.createElement('div');
      tooltip.className = 'custom-tooltip';
      tooltip.textContent = tooltipText;
      
      document.body.appendChild(tooltip);
      
      const rect = this.getBoundingClientRect();
      tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
      tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
      tooltip.style.opacity = '1';
      
      this.addEventListener('mouseleave', function() {
        tooltip.remove();
      });
    });
  });
}

// Añadir animaciones de entrada
function addEntryAnimations() {
  const elements = document.querySelectorAll('.card, .ui.table, .ui.form');
  
  elements.forEach((element, index) => {
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';
    element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    setTimeout(() => {
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    }, 100 + (index * 100));
  });
}

// Inicializar validación de formularios
function initFormValidation() {
  const forms = document.querySelectorAll('.ui.form');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(event) {
      let isValid = true;
      const requiredFields = form.querySelectorAll('input[required], select[required]');
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('error');
          
          // Crear mensaje de error si no existe
          let errorMessage = field.parentNode.querySelector('.error-message');
          if (!errorMessage) {
            errorMessage = document.createElement('div');
            errorMessage.className = 'error-message text-red-500 text-sm mt-1';
            errorMessage.textContent = 'Este campo es obligatorio';
            field.parentNode.appendChild(errorMessage);
          }
        } else {
          field.classList.remove('error');
          const errorMessage = field.parentNode.querySelector('.error-message');
          if (errorMessage) {
            errorMessage.remove();
          }
        }
      });
      
      if (!isValid) {
        event.preventDefault();
      }
    });
    
    // Limpiar errores al escribir
    form.querySelectorAll('input, select').forEach(field => {
      field.addEventListener('input', function() {
        this.classList.remove('error');
        const errorMessage = this.parentNode.querySelector('.error-message');
        if (errorMessage) {
          errorMessage.remove();
        }
      });
    });
  });
}

// Inicializar sistema de notificaciones
function initNotifications() {
  // Crear contenedor de notificaciones si no existe
  let notificationContainer = document.getElementById('notification-container');
  if (!notificationContainer) {
    notificationContainer = document.createElement('div');
    notificationContainer.id = 'notification-container';
    notificationContainer.className = 'fixed top-4 right-4 z-50 flex flex-col space-y-4';
    document.body.appendChild(notificationContainer);
  }
}

// Función para mostrar notificaciones
function showNotification(message, type = 'info', duration = 5000) {
  const container = document.getElementById('notification-container');
  
  const notification = document.createElement('div');
  notification.className = `notification ${type} bg-white shadow-lg rounded-lg p-4 flex items-center max-w-md transform transition-all duration-300 ease-in-out`;
  
  let icon = 'info-circle';
  let color = 'blue';
  
  if (type === 'success') {
    icon = 'check-circle';
    color = 'green';
  } else if (type === 'error') {
    icon = 'exclamation-circle';
    color = 'red';
  } else if (type === 'warning') {
    icon = 'exclamation-triangle';
    color = 'yellow';
  }
  
  notification.innerHTML = `
    <div class="flex-shrink-0 text-${color}-500">
      <i class="fas fa-${icon} text-xl"></i>
    </div>
    <div class="ml-3 flex-1">
      <p class="text-sm text-gray-800">${message}</p>
    </div>
    <div class="ml-4 flex-shrink-0 flex">
      <button class="inline-flex text-gray-400 hover:text-gray-500">
        <i class="fas fa-times"></i>
      </button>
    </div>
  `;
  
  container.appendChild(notification);
  
  // Animación de entrada
  setTimeout(() => {
    notification.classList.add('translate-x-0');
  }, 10);
  
  // Configurar cierre de notificación
  const closeButton = notification.querySelector('button');
  closeButton.addEventListener('click', () => {
    closeNotification(notification);
  });
  
  // Auto cerrar después de la duración
  if (duration > 0) {
    setTimeout(() => {
      closeNotification(notification);
    }, duration);
  }
}

// Función para cerrar notificaciones
function closeNotification(notification) {
  notification.classList.add('opacity-0', '-translate-y-2');
  
  setTimeout(() => {
    notification.remove();
  }, 300);
}

// Función para confirmar acciones
function confirmAction(message, onConfirm, onCancel) {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>
    <div class="bg-white rounded-lg overflow-hidden shadow-xl transform transition-all max-w-lg w-full">
      <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
        <div class="sm:flex sm:items-start">
          <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
            <i class="fas fa-exclamation-triangle text-red-600"></i>
          </div>
          <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Confirmar acción</h3>
            <div class="mt-2">
              <p class="text-sm text-gray-500">${message}</p>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
        <button id="confirm-btn" type="button" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm">
          Confirmar
        </button>
        <button id="cancel-btn" type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
          Cancelar
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Animación de entrada
  setTimeout(() => {
    modal.querySelector('div:nth-child(2)').classList.add('scale-100');
  }, 10);
  
  // Configurar botones
  const confirmBtn = modal.querySelector('#confirm-btn');
  const cancelBtn = modal.querySelector('#cancel-btn');
  
  confirmBtn.addEventListener('click', () => {
    closeModal();
    if (onConfirm) onConfirm();
  });
  
  cancelBtn.addEventListener('click', () => {
    closeModal();
    if (onCancel) onCancel();
  });
  
  function closeModal() {
    modal.querySelector('div:nth-child(2)').classList.add('opacity-0', 'scale-95');
    modal.querySelector('div:nth-child(1)').classList.add('opacity-0');
    
    setTimeout(() => {
      modal.remove();
    }, 300);
  }
}