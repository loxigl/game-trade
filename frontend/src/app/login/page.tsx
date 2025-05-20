'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';

// Компонент с использованием useSearchParams
function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const redirected = useRef(false);
  const searchParams = useSearchParams();
  
  // Проверяем, был ли пользователь перенаправлен из-за ошибки аутентификации
  const wasRedirected = searchParams?.get('redirected') === 'true';
  const redirectFrom = searchParams?.get('from') || null;
  
  // Для отладки
  useEffect(() => {
    if (typeof window !== 'undefined') {
      console.log('Login page loaded. Auth state:', {
        isAuthenticated,
        isLoading,
        wasRedirected,
        redirectFrom,
        accessToken: !!localStorage.getItem('accessToken'),
        refreshToken: !!localStorage.getItem('refreshToken'),
        token: !!localStorage.getItem('token')
      });
    }
  }, [isAuthenticated, isLoading, wasRedirected, redirectFrom]);
  
  // Если redirected=true, показываем сообщение об ошибке
  useEffect(() => {
    if (wasRedirected && !error) {
      const errorMessage = redirectFrom 
        ? `Сессия истекла или вы не авторизованы при доступе к ${redirectFrom}. Пожалуйста, войдите снова.`
        : 'Сессия истекла или вы не авторизованы. Пожалуйста, войдите снова.';
      setError(errorMessage);
    }
  }, [wasRedirected, error, redirectFrom]);

  // Проверяем, нужно ли сделать редирект, используя ref для отслеживания
  useEffect(() => {
    // Если пользователь был перенаправлен из-за ошибки аутентификации,
    // не делаем автоматический редирект обратно, чтобы избежать цикла
    if (!isLoading && isAuthenticated && !redirected.current && !wasRedirected) {
      redirected.current = true; // Помечаем, что редирект уже выполнен
      console.log('Redirecting to home after successful authentication');
      router.push('/');
    }
  }, [isAuthenticated, isLoading, router, wasRedirected]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (!email || !password) {
        throw new Error('Пожалуйста, заполните все поля');
      }

      console.log('Attempting login with email:', email);
      await login({ email, password });
      console.log('Login successful, tokens set');
      // Сбрасываем флаг redirected, чтобы useEffect мог выполнить редирект
      redirected.current = false;
      // Редирект выполнится через useEffect
    } catch (err) {
      console.error('Login error:', err);
      setError('Неверный email или пароль');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Убираем эту проверку, чтобы избежать преждевременного возврата null
  // if (isAuthenticated) {
  //   return null; // Редирект происходит в useEffect
  // }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-md">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Вход в аккаунт
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Или{' '}
            <Link href="/register" className="font-medium text-blue-600 hover:text-blue-500">
              зарегистрируйтесь, если у вас еще нет аккаунта
            </Link>
          </p>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">
                Email
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Пароль
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Пароль"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                Запомнить меня
              </label>
            </div>

            <div className="text-sm">
              <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-500">
                Забыли пароль?
              </Link>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white ${
                isSubmitting
                  ? 'bg-blue-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              }`}
            >
              {isSubmitting ? 'Выполняется вход...' : 'Войти'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Фолбэк для Suspense
function LoginFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-md">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Загрузка...
          </h2>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { isLoading } = useAuth();

  // Показываем индикатор загрузки
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <p>Загрузка...</p>
      </div>
    );
  }

  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  );
} 