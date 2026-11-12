import { useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import { AppRouter } from './router';

/** 应用根：启动时校验登录态，然后交给路由。 */
export default function App() {
  const { bootstrap } = useAuth();
  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);
  return <AppRouter />;
}
