import React, { useState } from 'react';
import Modal from './Modal'; // Assuming Modal.jsx is in the same directory

function SettingsPage({ username }) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [loading, setLoading] = useState(false);

  // Modal state for feedback
  const [modal, setModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'info'
  });

  const showModal = (title, message, type = 'info') => {
    setModal({ isOpen: true, title, message, type });
  };

  const closeModal = () => {
    setModal({ isOpen: false, title: '', message: '', type: 'info' });
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setLoading(true);

    if (newPassword !== confirmNewPassword) {
      showModal('Password Mismatch', 'New password and confirmation do not match.', 'error');
      setLoading(false);
      return;
    }

    if (newPassword.length < 6) { // Basic validation
      showModal('Password Too Short', 'New password must be at least 6 characters long.', 'error');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:5000/change_password/${username}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        showModal('Success', data.message, 'success');
        setOldPassword('');
        setNewPassword('');
        setConfirmNewPassword('');
      } else {
        showModal('Error', data.error || 'Failed to change password.', 'error');
      }
    } catch (error) {
      console.error('Error changing password:', error);
      showModal('Network Error', 'Could not connect to the server. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-xl shadow-lg">
      <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
        Change Password
      </h3>

      <form onSubmit={handleChangePassword} className="space-y-4">
        <div>
          <label htmlFor="oldPassword" className="block text-gray-700 text-sm font-bold mb-2">
            Old Password:
          </label>
          <input
            type="password"
            id="oldPassword"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div>
          <label htmlFor="newPassword" className="block text-gray-700 text-sm font-bold mb-2">
            New Password:
          </label>
          <input
            type="password"
            id="newPassword"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div>
          <label htmlFor="confirmNewPassword" className="block text-gray-700 text-sm font-bold mb-2">
            Confirm New Password:
          </label>
          <input
            type="password"
            id="confirmNewPassword"
            className="shadow appearance-none border rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={confirmNewPassword}
            onChange={(e) => setConfirmNewPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-blue-700 transition duration-300 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75"
          disabled={loading}
        >
          {loading ? 'Changing...' : 'Change Password'}
        </button>
      </form>

      {/* Modal Component */}
      {modal.isOpen && (
        <Modal
          title={modal.title}
          message={modal.message}
          type={modal.type}
          onClose={closeModal}
        />
      )}
    </div>
  );
}

export default SettingsPage;
