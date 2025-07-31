import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, DollarSign, Package, Clock, Star, TrendingUp, Calendar } from 'lucide-react'

const EarningsPanel = () => {
  const navigate = useNavigate()
  const [selectedPeriod, setSelectedPeriod] = useState('today')
  
  const [earnings] = useState({
    today: {
      total: 89.50,
      deliveries: 8,
      hours: 6.5,
      average_per_delivery: 11.19,
      rating: 4.8
    },
    week: {
      total: 456.80,
      deliveries: 42,
      hours: 28.5,
      average_per_delivery: 10.88,
      rating: 4.7
    },
    month: {
      total: 1834.20,
      deliveries: 167,
      hours: 112,
      average_per_delivery: 10.98,
      rating: 4.8
    }
  })

  const [recentDeliveries] = useState([
    {
      id: 15,
      pickup_address: 'Shopping Center',
      delivery_address: 'Residencial Park',
      earnings: 14.50,
      completed_at: '16:45',
      rating: 5
    },
    {
      id: 14,
      pickup_address: 'Centro Empresarial',
      delivery_address: 'Bairro Novo',
      earnings: 12.80,
      completed_at: '15:20',
      rating: 4
    },
    {
      id: 13,
      pickup_address: 'Rua Principal, 123',
      delivery_address: 'Avenida Central, 456',
      earnings: 9.90,
      completed_at: '14:10',
      rating: 5
    }
  ])

  const currentData = earnings[selectedPeriod]

  const getPeriodLabel = (period) => {
    switch (period) {
      case 'today':
        return 'Hoje'
      case 'week':
        return 'Esta Semana'
      case 'month':
        return 'Este Mês'
      default:
        return 'Hoje'
    }
  }

  const renderStars = (rating) => {
    return (
      <div className="flex items-center">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-3 h-3 ${
              star <= rating ? 'text-yellow-400 fill-current' : 'text-gray-400'
            }`}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="min-h-screen levo-bg-dark p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Button
            onClick={() => navigate('/delivery-person')}
            className="levo-button-secondary mr-4"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <h1 className="text-2xl font-bold text-white">Meus Ganhos</h1>
        </div>
        <TrendingUp className="w-6 h-6 levo-text-primary" />
      </div>

      {/* Period Selector */}
      <div className="flex space-x-2 mb-6">
        {['today', 'week', 'month'].map((period) => (
          <Button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`flex-1 ${
              selectedPeriod === period
                ? 'levo-button-primary'
                : 'levo-button-secondary'
            }`}
          >
            {getPeriodLabel(period)}
          </Button>
        ))}
      </div>

      {/* Main Earnings Card */}
      <Card className="levo-card mb-6">
        <CardContent className="p-6">
          <div className="text-center mb-4">
            <div className="text-3xl font-bold levo-text-primary mb-2">
              R$ {currentData.total.toFixed(2)}
            </div>
            <div className="levo-text-secondary">
              Ganhos {getPeriodLabel(selectedPeriod).toLowerCase()}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-xl font-bold text-white">{currentData.deliveries}</div>
              <div className="text-sm levo-text-secondary">Entregas</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-white">{currentData.hours}h</div>
              <div className="text-sm levo-text-secondary">Horas Online</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <DollarSign className="w-6 h-6 levo-text-primary mx-auto mb-2" />
            <div className="text-lg font-bold text-white">
              R$ {currentData.average_per_delivery.toFixed(2)}
            </div>
            <div className="text-xs levo-text-secondary">Média por entrega</div>
          </CardContent>
        </Card>
        
        <Card className="levo-card">
          <CardContent className="p-4 text-center">
            <Star className="w-6 h-6 levo-text-primary mx-auto mb-2" />
            <div className="text-lg font-bold text-white">{currentData.rating}</div>
            <div className="text-xs levo-text-secondary">Avaliação média</div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Insights */}
      <Card className="levo-card mb-6">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            Performance
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="levo-text-secondary">Ganho por hora:</span>
              <span className="text-white font-semibold">
                R$ {(currentData.total / currentData.hours).toFixed(2)}/h
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="levo-text-secondary">Taxa de aceitação:</span>
              <span className="text-white font-semibold">92%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="levo-text-secondary">Tempo médio por entrega:</span>
              <span className="text-white font-semibold">
                {Math.round((currentData.hours * 60) / currentData.deliveries)} min
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Deliveries */}
      <Card className="levo-card mb-6">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Package className="w-5 h-5 mr-2" />
            Entregas Recentes
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="space-y-3">
            {recentDeliveries.map((delivery) => (
              <div key={delivery.id} className="flex justify-between items-center p-3 levo-bg-dark rounded-lg">
                <div className="flex-1">
                  <div className="text-white text-sm font-medium">
                    Entrega #{delivery.id}
                  </div>
                  <div className="text-xs levo-text-secondary">
                    {delivery.pickup_address} → {delivery.delivery_address}
                  </div>
                  <div className="flex items-center mt-1">
                    <Clock className="w-3 h-3 levo-text-secondary mr-1" />
                    <span className="text-xs levo-text-secondary">{delivery.completed_at}</span>
                    <div className="ml-2">
                      {renderStars(delivery.rating)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold levo-text-primary">
                    R$ {delivery.earnings.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="space-y-3">
        <Button
          onClick={() => navigate('/delivery-person')}
          className="w-full levo-button-primary h-12"
        >
          <Package className="w-5 h-5 mr-2" />
          Voltar às Entregas
        </Button>
        
        <Button
          className="w-full levo-button-secondary h-12"
        >
          <Calendar className="w-5 h-5 mr-2" />
          Ver Relatório Completo
        </Button>
      </div>
    </div>
  )
}

export default EarningsPanel

