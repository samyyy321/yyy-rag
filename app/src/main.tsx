import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

import './styles/global.css';

const queryClient = new QueryClient();
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('找不到应用挂载节点');
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
