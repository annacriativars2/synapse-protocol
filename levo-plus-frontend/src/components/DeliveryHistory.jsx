import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, Package, MapPin, Clock, Star, MessageCircle } from 'lucide-react'

const DeliveryHistory = () => {
  const navigate = useNavigate()
  const [deliveries] = useState([
    {
      id: 1,
      pickup_address: 'Rua Exemplo, 123',
      delivery_address: 'Avenida Principal, 456',
      item_type: 'documento',
      final_price: 12.50,
      status: 'delivered',
      delivered_at: '2024-12-11T13:30:00Z',
      delivery_person: 'João Silva',
      client_rating: 5,
      delivery_person_rating: 4
    },
    {
      id: 2,
      pickup_address: 'Travessa A, 789',
      delivery_address: 'Rua B, 321',
      item_type: 'objeto_pequeno',
      final_price: 15.80,
      status: 'delivered',
      delivered_at: '2024-12-10T16:45:00Z',
      delivery_person: 'Maria Santos',
      client_rating: 4,
      delivery_person_rating: 5
    },
    {
      id: 3,
      pickup_address: 'Centro Comercial, Loja 45',
      delivery_address: 'Residencial Park, Bloco C',
      item_type: 'encomenda_leve',
      final_price: 18.90,
      status: 'delivered',
      delivered_at: '2024-12-09T11:20:00Z',
      delivery_person: 'Carlos Lima',
      client_rating: null,
      delivery_person_rating: null
    }
  ])

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

  const getItemLabel = (itemType) => {
    switch (itemType) {
      case 'documento':
        return 'Documento'
      case 'objeto_pequeno':
        return 'Objeto Pequeno'
      case 'encomenda_leve':
        return 'Encomenda Leve'
      default:
        return 'Item'
    }
  }

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const renderStars = (rating) => {
    if (!rating) return <span className="levo-text-secondary text-sm">Não avaliado</span>
    
    return (
      <div className="flex items-center">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${
              star <= rating ? 'text-yellow-400 fill-current' : 'text-gray-400'
            }`}
          />
        ))}
        <span className="ml-1 text-sm text-white">{rating}</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen levo-bg-dark p-4">
      {/* Header */}
      <div className="flex items-center mb-6">
        <Button
          onClick={() => navigate('/client')}
          className="levo-button-secondary mr-4"
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-2xl font-bold text-white">Histórico de Entregas</h1>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Package className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">{deliveries.length}</div>
            <div className="text-xs levo-text-secondary">Total</div>
          </CardContent>
        </Card>
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Star className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">4.7</div>
            <div className="text-xs levo-text-secondary">Sua Avaliação</div>
          </CardContent>
        </Card>
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Clock className="w-6 h-6 levo-text-primary mx-auto mb-1" />
            <div className="text-lg font-bold text-white">R$ 47,20</div>
            <div className="text-xs levo-text-secondary">Gasto Total</div>
          </CardContent>
        </Card>
      </div>

      {/* Deliveries List */}
      <div className="space-y-4">
        {deliveries.map((delivery) => (
          <Card key={delivery.id} className="levo-card">
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center">
                  <span className="text-2xl mr-3">{getItemIcon(delivery.item_type)}</span>
                  <div>
                    <div className="text-white font-semibold">
                      Entrega #{delivery.id}
                    </div>
                    <div className="text-sm levo-text-secondary">
                      {getItemLabel(delivery.item_type)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold levo-text-primary">
                    R$ {delivery.final_price.toFixed(2)}
                  </div>
                  <div className="text-xs levo-text-secondary">
                    {formatDate(delivery.delivered_at)}
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-3">
                <div className="flex items-center">
                  <MapPin className="w-4 h-4 levo-text-primary mr-2" />
                  <span className="text-sm text-white">{delivery.pickup_address}</span>
                </div>
                <div className="flex items-center">
                  <MapPin className="w-4 h-4 text-red-400 mr-2" />
                  <span className="text-sm text-white">{delivery.delivery_address}</span>
                </div>
              </div>

              <div className="flex justify-between items-center mb-3">
                <div>
                  <div className="text-sm levo-text-secondary">Entregador:</div>
                  <div className="text-white">{delivery.delivery_person}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm levo-text-secondary">Sua avaliação:</div>
                  {renderStars(delivery.client_rating)}
                </div>
              </div>

              <div className="flex space-x-2">
                <Button
                  onClick={() => navigate(`/tracking/${delivery.id}`)}
                  className="flex-1 levo-button-secondary"
                >
                  Ver Detalhes
                </Button>
                <Button
                  onClick={() => navigate(`/chat/${delivery.id}`)}
                  className="flex-1 levo-button-secondary"
                >
                  <MessageCircle className="w-4 h-4 mr-1" />
                  Chat
                </Button>
                {!delivery.client_rating && (
                  <Button className="flex-1 levo-button-primary">
                    Avaliar
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {deliveries.length === 0 && (
        <Card className="levo-card">
          <CardContent className="p-8 text-center">
            <Package className="w-16 h-16 levo-text-secondary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">
              Nenhuma entrega encontrada
            </h3>
            <p className="levo-text-secondary mb-4">
              Você ainda não fez nenhuma entrega
            </p>
            <Button
              onClick={() => navigate('/request-delivery')}
              className="levo-button-primary"
            >
              Fazer Primeira Entrega
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default DeliveryHistory

