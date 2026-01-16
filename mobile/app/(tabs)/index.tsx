/**
 * Photos tab - main gallery view.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
  Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { assetsApi } from '../../src/services/api';
import { useAuthStore } from '../../src/stores/authStore';

interface Asset {
  id: string;
  thumb_path: string | null;
  captured_at: string | null;
  is_favorite: boolean;
}

const COLUMN_COUNT = 3;
const SCREEN_WIDTH = Dimensions.get('window').width;
const ITEM_SIZE = SCREEN_WIDTH / COLUMN_COUNT - 2;

export default function PhotosScreen() {
  const router = useRouter();
  const { serverUrl } = useAuthStore();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadAssets = useCallback(async (pageNum: number, refresh = false) => {
    try {
      const response = await assetsApi.list(pageNum, 50);

      if (refresh) {
        setAssets(response.items);
      } else {
        setAssets((prev) => [...prev, ...response.items]);
      }

      setHasMore(response.has_more);
      setPage(pageNum);
    } catch (error) {
      console.error('Failed to load assets:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAssets(1, true);
  }, [loadAssets]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    loadAssets(1, true);
  }, [loadAssets]);

  const handleLoadMore = useCallback(() => {
    if (!loading && hasMore) {
      loadAssets(page + 1);
    }
  }, [loading, hasMore, page, loadAssets]);

  const renderItem = useCallback(
    ({ item }: { item: Asset }) => {
      const thumbUrl = item.thumb_path
        ? `${serverUrl}/api/v1/assets/${item.id}/thumbnail`
        : null;

      return (
        <Pressable
          style={styles.item}
          onPress={() => router.push(`/asset/${item.id}`)}
        >
          {thumbUrl ? (
            <Image source={{ uri: thumbUrl }} style={styles.image} />
          ) : (
            <View style={[styles.image, styles.placeholder]}>
              <Text style={styles.placeholderText}>No thumbnail</Text>
            </View>
          )}
        </Pressable>
      );
    },
    [serverUrl, router]
  );

  if (loading && assets.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.text}>Loading...</Text>
      </View>
    );
  }

  if (!loading && assets.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.text}>No photos yet</Text>
        <Text style={styles.subtext}>
          Upload photos from the web or enable auto-sync
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={assets}
      renderItem={renderItem}
      keyExtractor={(item) => item.id}
      numColumns={COLUMN_COUNT}
      contentContainerStyle={styles.list}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
      }
      onEndReached={handleLoadMore}
      onEndReachedThreshold={0.5}
    />
  );
}

const styles = StyleSheet.create({
  list: {
    padding: 1,
  },
  item: {
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    margin: 1,
  },
  image: {
    width: '100%',
    height: '100%',
    backgroundColor: '#2d2d44',
  },
  placeholder: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    color: '#6b7280',
    fontSize: 10,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  text: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  subtext: {
    color: '#6b7280',
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
});
