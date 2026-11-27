import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ProfilesReadyProvider from './context/ProfilesReadyContext';
import { ToastProvider } from './components/toast/ToastProvider';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <ProfilesReadyProvider>
        <App />
      </ProfilesReadyProvider>
    </ToastProvider>
  </React.StrictMode>,
);
