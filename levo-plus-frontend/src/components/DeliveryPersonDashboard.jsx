import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MapPin, Package, Clock, Star, User, Truck, ToggleLeft, ToggleRight } from 'lucide-react'

const DeliveryPersonDashboard = () => {
  const navigate = useNavigate()
  const [isOnline, setIsOnline] = useState(false)
  const [availableDeliveries, setAvailableDeliveries] = useState([
    {
      id: 1,
      pickup_address: 'Rua A, 123',
      delivery_address: 'Avenida B, 456',
      distance: '2.3 km',
      estimated_price: 8.50,
      item_type: 'documento'
    },
    {
      id: 2,
      pickup_address: 'Travessa E, 456',
      delivery_address: 'Rua F, 321',
      distance: '1.8 km',
      estimated_price: 10.20,
      item_type: 'objeto_pequeno'
    }
  ])
  const [todayEarnings, setTodayEarnings] = useState(45.20)

  const toggleOnlineStatus = () => {
    setIsOnline(!isOnline)
  }

  const acceptDelivery = (deliveryId) => {
    // Remove delivery from available list
    setAvailableDeliveries(prev => prev.filter(d => d.id !== deliveryId))
    // Navigate to delivery details
    navigate(`/tracking/${deliveryId}`)
  }

  const getItemIcon = (itemType) => {
    switch (itemType) {
      case 'documento':
        return '📄'
      case 'objeto_pequeno':
        return '📦'
      case 'encomenda_leve':
        return '🎁'
      default:
        return '📦'
    }
  }

  return (
    <div className="min-h-screen levo-bg-dark p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-4">
          <Button
            onClick={toggleOnlineStatus}
            className={`flex items-center space-x-2 ${
              isOnline ? 'levo-button-primary' : 'levo-button-secondary'
            }`}
          >
            {isOnline ? (
              <ToggleRight className="w-5 h-5" />
            ) : (
              <ToggleLeft className="w-5 h-5" />
            )}
            <span>{isOnline ? 'Online' : 'Offline'}</span>
          </Button>
        </div>
        <div className="text-right">
          <div className="text-sm levo-text-secondary">Ganhos hoje:</div>
          <div className="text-xl font-bold levo-text-primary">R$ {todayEarnings.toFixed(2)}</div>
        </div>
      </div>

      {/* Status Message */}
      {!isOnline && (
        <Card className="levo-card mb-6">
          <CardContent className="p-4 text-center">
            <Truck className="w-12 h-12 levo-text-secondary mx-auto mb-2" />
            <h3 className="text-lg font-semibold text-white mb-2">Você está offline</h3>
            <p className="levo-text-secondary mb-4">
              Ative o modo online para receber solicitações de entrega
            </p>
            <Button onClick={toggleOnlineStatus} className="levo-button-primary">
              Ficar Online
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Available Deliveries */}
      {isOnline && (
        <div className="mb-6">
          <div className="flex items-center mb-4">
            <MapPin className="w-5 h-5 levo-text-primary mr-2" />
            <h2 className="text-xl font-semibold text-white">Entregas Disponíveis</h2>
          </div>
          
          {availableDeliveries.length === 0 ? (
            <Card className="levo-card">
              <CardContent className="p-6 text-center">
                <Package className="w-12 h-12 levo-text-secondary mx-auto mb-2" />
                <p className="levo-text-secondary">Nenhuma entrega disponível no momento</p>
                <p className="text-sm levo-text-secondary mt-1">
                  Aguarde novas solicitações...
                </p>
              </CardContent>
            </Card>
          ) : (
            availableDeliveries.map((delivery) => (
              <Card key={delivery.id} className="levo-card mb-4">
                <CardContent className="p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <span className="text-2xl mr-2">{getItemIcon(delivery.item_type)}</span>
                        <div>
                          <div className="flex items-center">
                            <MapPin className="w-4 h-4 levo-text-primary mr-1" />
                            <span className="text-white text-sm">{delivery.pickup_address}</span>
                          </div>
                          <div className="flex items-center mt-1">
                            <MapPin className="w-4 h-4 text-red-400 mr-1" />
                            <span className="text-white text-sm">{delivery.delivery_address}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm levo-text-secondary">{delivery.distance}</div>
                      <div className="text-lg font-bold levo-text-primary">
                        R$ {delivery.estimated_price.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => acceptDelivery(delivery.id)}
                    className="w-full levo-button-primary"
                  >
                    ACEITAR
                  </Button>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Package className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">8</div>
            <div className="text-xs levo-text-secondary">Entregas hoje</div>
          </CardContent>
        </Card>
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Clock className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">6h 30min</div>
            <div className="text-xs levo-text-secondary">Tempo online</div>
          </CardContent>
        </Card>
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Star className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">4.8</div>
            <div className="text-xs levo-text-secondary">Avaliação</div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 levo-bg-card border-t border-gray-600 p-4">
        <div className="flex justify-around">
          <Button
            onClick={() => navigate('/delivery-person')}
            className="flex flex-col items-center levo-button-primary"
          >
            <Truck className="w-5 h-5 mb-1" />
            <span className="text-xs">Disponível</span>
          </Button>
          <Button
            onClick={() => navigate('/earnings')}
            className="flex flex-col items-center levo-button-secondary"
          >
            <Star className="w-5 h-5 mb-1" />
            <span className="text-xs">Ganhos</span>
          </Button>
          <Button
            onClick={() => navigate('/login')}
            className="flex flex-col items-center levo-button-secondary"
          >
            <User className="w-5 h-5 mb-1" />
            <span className="text-xs">Perfil</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

export default DeliveryPersonDashboard

