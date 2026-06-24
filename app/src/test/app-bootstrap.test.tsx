import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import App from '../App';

/** 为依赖 QueryClient 的根组件提供最小测试运行环境。 */
function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

test('显示知识库工作台标题', () => {
  renderApp();
  expect(screen.getByRole('heading', { name: '知识库工作台' })).toBeInTheDocument();
});
