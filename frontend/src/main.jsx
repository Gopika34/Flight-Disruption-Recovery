import React from 'react';
import { createRoot } from 'react-dom/client';
import { ClerkProvider } from '@clerk/react';
import App from './App.jsx';
import { ClerkAuthBootstrap, GuestAuthBootstrap } from './components/auth/AuthBootstrap.jsx';
import './index.css';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const app = <App />;
const root = publishableKey
  ? <ClerkProvider publishableKey={publishableKey}>
      <ClerkAuthBootstrap>{app}</ClerkAuthBootstrap>
    </ClerkProvider>
  : <GuestAuthBootstrap>{app}</GuestAuthBootstrap>;
  
createRoot(document.getElementById('root')).render(<React.StrictMode>{root}</React.StrictMode>);
