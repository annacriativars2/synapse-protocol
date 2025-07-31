import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MapPin, Package, Clock, Star, User, Truck } from 'lucide-react'

const ClientDashboard = () => {
  const navigate = useNavigate()
  const [activeDeliveries, setActiveDeliveries] = useState([
    {
      id: 1,
      status: 'in_transit',
      pickup_address: 'Rua Exemplo, 123',
      delivery_address: 'Avenida Principal, 456',
      delivery_person: 'João Silva',
      estimated_time: 15
    }
  ])

  return (
    <div className="min-h-screen levo-bg-dark p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Olá, Cliente!</h1>
          <p className="levo-text-secondary">Pronto para uma nova entrega?</p>
        </div>
        <Button
          onClick={() => navigate('/history')}
          className="levo-button-secondary"
        >
          <User className="w-4 h-4 mr-2" />
          Perfil
        </Button>
      </div>

      {/* Quick Action */}
      <Card className="levo-card mb-6">
        <CardContent className="p-6">
          <Button
            onClick={() => navigate('/request-delivery')}
            className="w-full levo-button-primary h-16 text-xl font-bold"
          >
            <Package className="w-6 h-6 mr-3" />
            Solicitar Entrega
          </Button>
        </CardContent>
      </Card>

      {/* Active Deliveries */}
      {activeDeliveries.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Entregas Ativas</h2>
          {activeDeliveries.map((delivery) => (
            <Card key={delivery.id} className="levo-card mb-4">
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center mb-2">
                      <MapPin className="w-4 h-4 levo-text-primary mr-2" />
                      <span className="text-white text-sm">{delivery.pickup_address}</span>
                    </div>
                    <div className="flex items-center mb-2">
                      <MapPin className="w-4 h-4 text-red-400 mr-2" />
                      <span className="text-white text-sm">{delivery.delivery_address}</span>
                    </div>
                    <div className="flex items-center">
                      <Truck className="w-4 h-4 levo-text-secondary mr-2" />
                      <span className="levo-text-secondary text-sm">{delivery.delivery_person}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center mb-1">
                      <Clock className="w-4 h-4 levo-text-primary mr-1" />
                      <span className="levo-text-primary text-sm">{delivery.estimated_time} min</span>
                    </div>
                    <span className="text-xs levo-text-secondary">Em trânsito</span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Button
                    onClick={() => navigate(`/tracking/${delivery.id}`)}
                    className="flex-1 levo-button-primary"
                  >
                    Acompanhar
                  </Button>
                  <Button
                    onClick={() => navigate(`/chat/${delivery.id}`)}
                    className="flex-1 levo-button-secondary"
                  >
                    Chat
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Package className="w-8 h-8 levo-text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold text-white">12</div>
            <div className="text-sm levo-text-secondary">Entregas</div>
          </CardContent>
        </Card>
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Star className="w-8 h-8 levo-text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold text-white">4.8</div>
            <div className="text-sm levo-text-secondary">Avaliação</div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 levo-bg-card border-t border-gray-600 p-4">
        <div className="flex justify-around">
          <Button
            onClick={() => navigate('/client')}
            className="flex flex-col items-center levo-button-primary"
          >
            <Package className="w-5 h-5 mb-1" />
            <span className="text-xs">Home</span>
          </Button>
          <Button
            onClick={() => navigate('/history')}
            className="flex flex-col items-center levo-button-secondary"
          >
            <Clock className="w-5 h-5 mb-1" />
            <span className="text-xs">Histórico</span>
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

export default ClientDashboard

