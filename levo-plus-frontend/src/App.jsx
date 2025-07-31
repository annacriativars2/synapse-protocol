import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'

// Import components (to be created)
import LoginPage from './components/LoginPage'
import ClientDashboard from './components/ClientDashboard'
import DeliveryPersonDashboard from './components/DeliveryPersonDashboard'
import DeliveryRequest from './components/DeliveryRequest'
import DeliveryTracking from './components/DeliveryTracking'
import DeliveryHistory from './components/DeliveryHistory'
import EarningsPanel from './components/EarningsPanel'
import Chat from './components/Chat'

function App() {
  return (
    <Router>
      <div className="min-h-screen levo-bg-dark">
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/client" element={<ClientDashboard />} />
          <Route path="/delivery-person" element={<DeliveryPersonDashboard />} />
          <Route path="/request-delivery" element={<DeliveryRequest />} />
          <Route path="/tracking/:deliveryId" element={<DeliveryTracking />} />
          <Route path="/history" element={<DeliveryHistory />} />
          <Route path="/earnings" element={<EarningsPanel />} />
          <Route path="/chat/:deliveryId" element={<Chat />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App

