import React from 'react';

function Modal({ title, message, onClose, type = 'info' }) {
  let headerClasses = "bg-blue-500 text-white";
  let buttonClasses = "bg-blue-600 hover:bg-blue-700";

  if (type === 'success') {
    headerClasses = "bg-green-500 text-white";
    buttonClasses = "bg-green-600 hover:bg-green-700";
  } else if (type === 'error') {
    headerClasses = "bg-red-500 text-white";
    buttonClasses = "bg-red-600 hover:bg-red-700";
  } else if (type === 'confirm') {
    headerClasses = "bg-yellow-500 text-white";
    buttonClasses = "bg-yellow-600 hover:bg-yellow-700"; // For primary action in confirm
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-auto overflow-hidden">
        <div className={`px-6 py-4 ${headerClasses}`}>
          <h3 className="text-xl font-semibold">{title}</h3>
        </div>
        <div className="p-6 text-gray-700">
          <p>{message}</p>
        </div>
        <div className="px-6 py-4 bg-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className={`py-2 px-4 rounded-lg font-semibold text-white transition duration-300 ease-in-out ${buttonClasses} shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-opacity-75`}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default Modal;
