/**
 * Root layout for Expo Router.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { useAuthStore } from '../src/stores/authStore';

export default function RootLayout() {
  const { loadToken, isLoading, isAuthenticated } = useAuthStore();

  useEffect(() => {
    loadToken();
  }, []);

  if (isLoading) {
    return null; // Or splash screen
  }

  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: '#1a1a2e' },
          headerTintColor: '#fff',
          contentStyle: { backgroundColor: '#0f0f1a' },
        }}
      >
        {isAuthenticated ? (
          <>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="asset/[id]" options={{ title: 'Photo' }} />
            <Stack.Screen name="album/[id]" options={{ title: 'Album' }} />
            <Stack.Screen name="person/[id]" options={{ title: 'Person' }} />
          </>
        ) : (
          <>
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen name="setup" options={{ title: 'Server Setup' }} />
          </>
        )}
      </Stack>
    </>
  );
}
