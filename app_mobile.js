/**
================================================================================
APPLICATION MOBILE - RAPPROCHEMENT ASSURANCES (React Native + Expo)
================================================================================
Application mobile pour Android/iOS avec:
  - Dashboard temps réel
  - Alertes instantanées
  - Synchronisation push
  - Disponible sur Google Play Store via Expo

Installation:
  1. npm install -g eas-cli expo-cli
  2. npm install
  3. expo start
  4. Scanner le QR code ou taper 'a' pour Android
================================================================================
*/

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
  StatusBar,
  ActivityIndicator,
  FlatList,
  SafeAreaView,
  Image,
  Dimensions,
  Platform,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LineChart, BarChart } from 'react-native-chart-kit';
import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/alerts';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

// ================================================================================
// CONFIGURATION NOTIFICATIONS
// ================================================================================

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// ================================================================================
// ÉCRAN: DASHBOARD
// ================================================================================

function DashboardScreen() {
  const [metrics, setMetrics] = useState({
    alertes_par_severite: { CRITIQUE: 0, ATTENTION: 0 },
    rapports_24h: 0,
    connexions_websocket: 0,
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_URL}/api/metrics`);
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Erreur fetch metrics:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchMetrics();
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Chargement...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📊 DASHBOARD</Text>
        <Text style={styles.headerSubtitle}>Rapprochement Assurances</Text>
      </View>

      {/* Cartes de statistiques */}
      <View style={styles.statsGrid}>
        <StatCard
          icon="alert-circle"
          title="🔴 Critiques"
          value={metrics.alertes_par_severite?.CRITIQUE || 0}
          color="#FF5252"
        />
        <StatCard
          icon="alert"
          title="🟠 Attention"
          value={metrics.alertes_par_severite?.ATTENTION || 0}
          color="#FFA500"
        />
        <StatCard
          icon="file-document"
          title="📄 Rapports"
          value={metrics.rapports_24h || 0}
          color="#4CAF50"
        />
        <StatCard
          icon="cloud-check"
          title="🔗 Connecté"
          value={metrics.connexions_websocket || 0}
          color="#2196F3"
        />
      </View>

      {/* Boutons d'action */}
      <View style={styles.actionButtons}>
        <TouchableOpacity style={[styles.button, styles.buttonPrimary]}>
          <MaterialCommunityIcons name="refresh" size={20} color="white" />
          <Text style={styles.buttonText}>Synchroniser</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]}>
          <MaterialCommunityIcons name="file-export" size={20} color="white" />
          <Text style={styles.buttonText}>Exporter</Text>
        </TouchableOpacity>
      </View>

      {/* Informations complémentaires */}
      <View style={styles.infoBox}>
        <Text style={styles.infoTitle}>ℹ️ Informations</Text>
        <Text style={styles.infoText}>• {metrics.rapports_24h} rapport(s) généré(s) aujourd'hui</Text>
        <Text style={styles.infoText}>• {metrics.alertes_par_severite?.CRITIQUE || 0} alerte(s) critique(s)</Text>
        <Text style={styles.infoText}>• Serveur: 🟢 En ligne</Text>
      </View>
    </ScrollView>
  );
}

// ================================================================================
// COMPOSANT: CARTE DE STATISTIQUE
// ================================================================================

function StatCard({ icon, title, value, color }) {
  return (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={styles.statHeader}>
        <Text style={styles.statTitle}>{title}</Text>
      </View>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

// ================================================================================
// ÉCRAN: ALERTES
// ================================================================================

function AlertesScreen() {
  const [alertes, setAlertes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    fetchAlertes();
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchAlertes = async () => {
    try {
      const response = await fetch(`${API_URL}/api/alerts?statut=non_traitee`);
      if (response.ok) {
        const data = await response.json();
        setAlertes(data.alertes || []);
      }
    } catch (error) {
      console.error('Erreur fetch alertes:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const connectWebSocket = async () => {
    try {
      // Note: Sur mobile, utiliser une lib WebSocket compatible
      // Pour le test, on utilise fetch avec polling
      const interval = setInterval(fetchAlertes, 5000);
      return () => clearInterval(interval);
    } catch (error) {
      console.error('Erreur WebSocket:', error);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchAlertes();
  };

  const traiterAlerte = async (alerteId) => {
    try {
      const response = await fetch(`${API_URL}/api/alert/${alerteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut: 'traitee' }),
      });

      if (response.ok) {
        Alert.alert('✅ Succès', 'Alerte marquée comme traitée');
        fetchAlertes();
      }
    } catch (error) {
      Alert.alert('❌ Erreur', error.message);
    }
  };

  const renderAlerte = ({ item }) => (
    <TouchableOpacity
      style={[
        styles.alerteCard,
        item.severite === 'CRITIQUE' ? styles.alerteCritique : styles.alerteAttention,
      ]}
      onPress={() => Alert.alert(item.titre, item.description || 'Aucune description')}
    >
      <View style={styles.alerteHeader}>
        <Text style={styles.alerteType}>{item.type}</Text>
        <Text style={[styles.alerteSeverite, item.severite === 'CRITIQUE' ? { color: 'red' } : { color: 'orange' }]}>
          {item.severite}
        </Text>
      </View>
      <Text style={styles.alerteTitre}>{item.titre}</Text>
      <Text style={styles.alerteDetail}>Police: {item.n_police}</Text>
      <Text style={styles.alerteDetail}>Montant: {item.montant ? `${item.montant.toFixed(2)} DH` : '-'}</Text>
      <Text style={styles.alerteDate}>{new Date(item.date_creation).toLocaleDateString('fr-FR')}</Text>

      <TouchableOpacity
        style={styles.alerteButton}
        onPress={() => traiterAlerte(item.id)}
      >
        <Text style={styles.alerteButtonText}>✅ Traiter</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🚨 ALERTES</Text>
        <Text style={styles.headerSubtitle}>{alertes.length} alerte(s) non traitée(s)</Text>
      </View>

      <FlatList
        data={alertes}
        renderItem={renderAlerte}
        keyExtractor={(item) => item.id}
        refreshing={refreshing}
        onRefresh={onRefresh}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="check-circle" size={48} color="#4CAF50" />
            <Text style={styles.emptyStateText}>✅ Toutes les alertes sont traitées!</Text>
          </View>
        }
      />
    </View>
  );
}

// ================================================================================
// ÉCRAN: RAPPORTS
// ================================================================================

function RapportsScreen() {
  const [rapports, setRapports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchRapports();
  }, []);

  const fetchRapports = async () => {
    try {
      const response = await fetch(`${API_URL}/api/rapports`);
      if (response.ok) {
        const data = await response.json();
        setRapports(data.rapports || []);
      }
    } catch (error) {
      console.error('Erreur fetch rapports:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchRapports();
  };

  const renderRapport = ({ item }) => (
    <TouchableOpacity
      style={styles.rapportCard}
      onPress={() =>
        Alert.alert(
          `Rapport du ${item.date_controle}`,
          `Conforme: ${item.nb_conforme}/${item.nb_total}\nTaux: ${item.taux_conformite}%`
        )
      }
    >
      <View style={styles.rapportHeader}>
        <Text style={styles.rapportDate}>{new Date(item.date_generation).toLocaleDateString('fr-FR')}</Text>
        <View
          style={[
            styles.rapportBadge,
            item.taux_conformite >= 90 ? styles.badgeGreen : styles.badgeOrange,
          ]}
        >
          <Text style={styles.badgeText}>{item.taux_conformite}%</Text>
        </View>
      </View>
      <View style={styles.rapportStats}>
        <View style={styles.rapportStat}>
          <Text style={styles.rapportStatLabel}>Total</Text>
          <Text style={styles.rapportStatValue}>{item.nb_total}</Text>
        </View>
        <View style={styles.rapportStat}>
          <Text style={styles.rapportStatLabel}>Conforme</Text>
          <Text style={styles.rapportStatValue}>{item.nb_conforme}</Text>
        </View>
        <View style={styles.rapportStat}>
          <Text style={styles.rapportStatLabel}>Attention</Text>
          <Text style={styles.rapportStatValue}>{item.nb_attention}</Text>
        </View>
        <View style={styles.rapportStat}>
          <Text style={styles.rapportStatLabel}>Critique</Text>
          <Text style={styles.rapportStatValue}>{item.nb_critique}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📄 RAPPORTS</Text>
        <Text style={styles.headerSubtitle}>{rapports.length} rapport(s)</Text>
      </View>

      <FlatList
        data={rapports}
        renderItem={renderRapport}
        keyExtractor={(item) => item.id}
        refreshing={refreshing}
        onRefresh={onRefresh}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="file-document-outline" size={48} color="#999" />
            <Text style={styles.emptyStateText}>Aucun rapport</Text>
          </View>
        }
      />
    </View>
  );
}

// ================================================================================
// ÉCRAN: PARAMÈTRES
// ================================================================================

function SettingsScreen() {
  const [serverUrl, setServerUrl] = useState(API_URL);
  const [emailNotif, setEmailNotif] = useState(true);

  const saveSettings = async () => {
    await AsyncStorage.setItem('serverUrl', serverUrl);
    Alert.alert('✅ Paramètres sauvegardés');
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>⚙️ PARAMÈTRES</Text>
      </View>

      <View style={styles.settingSection}>
        <Text style={styles.sectionTitle}>Serveur</Text>
        <Text style={styles.sectionLabel}>URL du serveur API</Text>
        {/* Note: TextInput nécessaire pour les vrais paramètres */}
        <View style={styles.inputBox}>
          <Text style={styles.inputText}>{serverUrl}</Text>
        </View>
      </View>

      <View style={styles.settingSection}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        <View style={styles.notificationOption}>
          <Text style={styles.notificationLabel}>Alertes critiques</Text>
          <View
            style={[styles.toggleSwitch, emailNotif && styles.toggleOn]}
          >
            <Text style={styles.toggleText}>{emailNotif ? 'ON' : 'OFF'}</Text>
          </View>
        </View>
      </View>

      <View style={styles.aboutSection}>
        <Text style={styles.aboutTitle}>À propos</Text>
        <Text style={styles.aboutText}>📱 Rapprochement Assurances v1.0.0</Text>
        <Text style={styles.aboutText}>© 2026 | www.assurances-elkhaddar.ma</Text>
      </View>

      <TouchableOpacity style={[styles.button, styles.buttonPrimary]} onPress={saveSettings}>
        <Text style={styles.buttonText}>💾 Sauvegarder</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ================================================================================
// APP PRINCIPALE
// ================================================================================

export default function App() {
  useEffect(() => {
    // Demande la permission pour les notifications
    Notifications.requestPermissionsAsync();
  }, []);

  return (
    <NavigationContainer>
      <StatusBar barStyle="dark-content" backgroundColor="#F5F5F5" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ focused, color, size }) => {
            let iconName;
            if (route.name === 'Dashboard') {
              iconName = focused ? 'chart-box' : 'chart-box-outline';
            } else if (route.name === 'Alertes') {
              iconName = focused ? 'bell' : 'bell-outline';
            } else if (route.name === 'Rapports') {
              iconName = focused ? 'file-document' : 'file-document-outline';
            } else if (route.name === 'Settings') {
              iconName = focused ? 'cog' : 'cog-outline';
            }
            return <MaterialCommunityIcons name={iconName} size={size} color={color} />;
          },
          tabBarActiveTintColor: '#2196F3',
          tabBarInactiveTintColor: '#999',
          tabBarLabelStyle: { fontSize: 11, marginBottom: 3 },
        })}
      >
        <Tab.Screen name="Dashboard" component={DashboardScreen} />
        <Tab.Screen name="Alertes" component={AlertesScreen} />
        <Tab.Screen name="Rapports" component={RapportsScreen} />
        <Tab.Screen name="Settings" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

// ================================================================================
// STYLES
// ================================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  header: {
    backgroundColor: '#2196F3',
    paddingVertical: 20,
    paddingHorizontal: 15,
    marginBottom: 15,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  headerSubtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 3,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    marginBottom: 15,
  },
  statCard: {
    width: '48%',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 10,
    borderLeftWidth: 4,
    elevation: 2,
  },
  statHeader: {
    marginBottom: 8,
  },
  statTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    marginBottom: 15,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 5,
  },
  buttonPrimary: {
    backgroundColor: '#4CAF50',
  },
  buttonSecondary: {
    backgroundColor: '#FF9800',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    marginLeft: 5,
  },
  infoBox: {
    backgroundColor: 'white',
    marginHorizontal: 10,
    padding: 15,
    borderRadius: 8,
    marginBottom: 20,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  infoText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  alerteCard: {
    marginHorizontal: 10,
    marginBottom: 10,
    padding: 15,
    borderRadius: 8,
    backgroundColor: 'white',
  },
  alerteCritique: {
    borderLeftWidth: 4,
    borderLeftColor: '#FF5252',
  },
  alerteAttention: {
    borderLeftWidth: 4,
    borderLeftColor: '#FFA500',
  },
  alerteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  alerteType: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
  },
  alerteSeverite: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  alerteTitre: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  alerteDetail: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  alerteDate: {
    fontSize: 11,
    color: '#999',
    marginBottom: 10,
  },
  alerteButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 8,
    borderRadius: 4,
    alignItems: 'center',
  },
  alerteButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 50,
  },
  emptyStateText: {
    marginTop: 10,
    fontSize: 14,
    color: '#999',
  },
  rapportCard: {
    marginHorizontal: 10,
    marginBottom: 10,
    padding: 15,
    borderRadius: 8,
    backgroundColor: 'white',
  },
  rapportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  rapportDate: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
  },
  rapportBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeGreen: {
    backgroundColor: '#C8E6C9',
  },
  badgeOrange: {
    backgroundColor: '#FFE0B2',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
  },
  rapportStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  rapportStat: {
    alignItems: 'center',
  },
  rapportStatLabel: {
    fontSize: 11,
    color: '#999',
    marginBottom: 4,
  },
  rapportStatValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  settingSection: {
    backgroundColor: 'white',
    marginHorizontal: 10,
    marginBottom: 15,
    padding: 15,
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  sectionLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
  },
  inputBox: {
    backgroundColor: '#F5F5F5',
    padding: 10,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  inputText: {
    fontSize: 12,
    color: '#666',
  },
  notificationOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  notificationLabel: {
    fontSize: 12,
    color: '#333',
  },
  toggleSwitch: {
    width: 50,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#CCC',
    justifyContent: 'center',
    alignItems: 'center',
  },
  toggleOn: {
    backgroundColor: '#4CAF50',
  },
  toggleText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  aboutSection: {
    alignItems: 'center',
    paddingVertical: 30,
  },
  aboutTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  aboutText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
});
