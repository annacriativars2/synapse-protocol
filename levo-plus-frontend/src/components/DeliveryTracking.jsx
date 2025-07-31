import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { MapPin, Package, Clock, ArrowLeft, MessageCircle, Phone, User } from 'lucide-react'

const DeliveryTracking = () => {
  const { deliveryId } = useParams()
  const navigate = useNavigate()
  const [delivery, setDelivery] = useState({
    id: deliveryId,
    status: 'in_transit',
    pickup_address: 'Rua Exemplo, 123',
    delivery_address: 'Avenida Principal, 456',
    item_type: 'documento',
    estimated_price: 12.50,
    delivery_person: {
      name: 'João Silva',
      rating: 4.8,
      vehicle: 'Honda CG 160 - ABC-1234'
    },
    estimated_time: 15,
    progress: 60
  })

  const getStatusText = (status) => {
    const statusMap = {
      'pending': 'Aguardando entregador',
      'accepted': 'Entregador a caminho da retirada',
      'picked_up': 'Item coletado',
      'in_transit': 'A caminho da entrega',
      'delivered': 'Entregue',
      'cancelled': 'Cancelado'
    }
    return statusMap[status] || status
  }

  const getStatusColor = (status) => {
    const colorMap = {
      'pending': 'text-yellow-400',
      'accepted': 'text-blue-400',
      'picked_up': 'levo-text-primary',
      'in_transit': 'levo-text-primary',
      'delivered': 'text-green-400',
      'cancelled': 'text-red-400'
    }
    return colorMap[status] || 'levo-text-secondary'
  }

  return (
    <div className="min-h-screen levo-bg-dark p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Button
            onClick={() => navigate('/client')}
            className="levo-button-secondary mr-4"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-white">Entrega #{deliveryId}</h1>
            <p className={`text-sm ${getStatusColor(delivery.status)}`}>
              {getStatusText(delivery.status)}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center levo-text-primary">
            <Clock className="w-4 h-4 mr-1" />
            <span>{delivery.estimated_time} min</span>
          </div>
        </div>
      </div>

      {/* Map Placeholder */}
      <Card className="levo-card mb-6">
        <CardContent className="p-4">
          <div className="h-64 bg-gray-700 rounded-lg flex items-center justify-center relative">
            <div className="text-center">
              <MapPin className="w-12 h-12 levo-text-primary mx-auto mb-2" />
              <p className="levo-text-secondary">Mapa em tempo real</p>
              <p className="text-sm levo-text-secondary">
                Acompanhe a localização do entregador
              </p>
            </div>
            
            {/* Progress indicator */}
            <div className="absolute bottom-4 left-4 right-4">
              <div className="bg-gray-600 rounded-full h-2">
                <div 
                  className="bg-lime-400 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${delivery.progress}%` }}
                ></div>
              </div>
              <div className="text-xs levo-text-secondary mt-1 text-center">
                {delivery.progress}% concluído
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delivery Person Info */}
      <Card className="levo-card mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gray-600 rounded-full flex items-center justify-center mr-3">
                <User className="w-6 h-6 levo-text-primary" />
              </div>
              <div>
                <div className="text-white font-semibold">{delivery.delivery_person.name}</div>
                <div className="text-sm levo-text-secondary">{delivery.delivery_person.vehicle}</div>
                <div className="flex items-center">
                  <span className="text-yellow-400 text-sm">★ {delivery.delivery_person.rating}</span>
                </div>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button
                onClick={() => navigate(`/chat/${deliveryId}`)}
                className="levo-button-secondary"
              >
                <MessageCircle className="w-4 h-4" />
              </Button>
              <Button className="levo-button-secondary">
                <Phone className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delivery Details */}
      <Card className="levo-card mb-6">
        <CardContent className="p-4 space-y-4">
          <div>
            <div className="flex items-center mb-2">
              <MapPin className="w-4 h-4 levo-text-primary mr-2" />
              <span className="text-sm levo-text-secondary">Retirada</span>
            </div>
            <div className="text-white ml-6">{delivery.pickup_address}</div>
          </div>
          
          <div className="border-l-2 border-gray-600 ml-2 h-6"></div>
          
          <div>
            <div className="flex items-center mb-2">
              <MapPin className="w-4 h-4 text-red-400 mr-2" />
              <span className="text-sm levo-text-secondary">Entrega</span>
            </div>
            <div className="text-white ml-6">{delivery.delivery_address}</div>
          </div>
        </CardContent>
      </Card>

      {/* Item and Payment Info */}
      <Card className="levo-card mb-6">
        <CardContent className="p-4">
          <div className="flex justify-between items-center">
            <div>
              <div className="flex items-center mb-2">
                <Package className="w-4 h-4 levo-text-primary mr-2" />
                <span className="text-white">
                  {delivery.item_type === 'documento' ? 'Documento' :
                   delivery.item_type === 'objeto_pequeno' ? 'Objeto Pequeno' :
                   'Encomenda Leve'}
                </span>
              </div>
              <div className="text-sm levo-text-secondary">Pagamento via PIX</div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold levo-text-primary">
                R$ {delivery.estimated_price.toFixed(2)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="space-y-3">
        <Button
          onClick={() => navigate(`/chat/${deliveryId}`)}
          className="w-full levo-button-primary h-12"
        >
          <MessageCircle className="w-5 h-5 mr-2" />
          Conversar com Entregador
        </Button>
        
        {delivery.status === 'delivered' && (
          <Button
            onClick={() => navigate('/history')}
            className="w-full levo-button-secondary h-12"
          >
            Avaliar Entrega
          </Button>
        )}
      </div>
    </div>
  )
}

export default DeliveryTracking

