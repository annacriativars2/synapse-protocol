import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MapPin, Package, Clock, ArrowLeft, CreditCard } from 'lucide-react'

const DeliveryRequest = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    pickup_address: '',
    delivery_address: '',
    item_type: 'documento',
    item_description: '',
    payment_method: 'pix'
  })
  const [estimatedPrice, setEstimatedPrice] = useState(12.50)
  const [estimatedTime, setEstimatedTime] = useState(25)

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // Simulate price calculation
    if (field === 'item_type') {
      const multipliers = {
        'documento': 1.0,
        'objeto_pequeno': 1.2,
        'encomenda_leve': 1.5
      }
      setEstimatedPrice(8.0 * multipliers[value])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Simulate API call
    try {
      const response = await fetch('http://localhost:5000/api/deliveries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          client_id: 1, // Mock client ID
          estimated_price: estimatedPrice,
          estimated_time: estimatedTime
        }),
      })
      
      if (response.ok) {
        const result = await response.json()
        navigate(`/tracking/${result.delivery.id}`)
      }
    } catch (error) {
      console.error('Error creating delivery:', error)
      // For demo purposes, navigate anyway
      navigate('/tracking/1')
    }
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
        <h1 className="text-2xl font-bold text-white">Solicitar Entrega</h1>
      </div>

      {/* Map Placeholder */}
      <Card className="levo-card mb-6">
        <CardContent className="p-4">
          <div className="h-48 bg-gray-700 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <MapPin className="w-12 h-12 levo-text-primary mx-auto mb-2" />
              <p className="levo-text-secondary">Mapa de localização</p>
              <p className="text-sm levo-text-secondary">
                Visualização dos pontos de retirada e entrega
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Addresses */}
        <Card className="levo-card">
          <CardContent className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Local de Retirada
              </label>
              <div className="flex items-center">
                <MapPin className="w-4 h-4 levo-text-primary mr-2" />
                <Input
                  value={formData.pickup_address}
                  onChange={(e) => handleInputChange('pickup_address', e.target.value)}
                  className="levo-input flex-1"
                  placeholder="Rua Exemplo, 123"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Local de Entrega
              </label>
              <div className="flex items-center">
                <MapPin className="w-4 h-4 text-red-400 mr-2" />
                <Input
                  value={formData.delivery_address}
                  onChange={(e) => handleInputChange('delivery_address', e.target.value)}
                  className="levo-input flex-1"
                  placeholder="Avenida Principal, 456"
                  required
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Item Type */}
        <Card className="levo-card">
          <CardContent className="p-4">
            <label className="block text-sm font-medium text-white mb-3">
              Tipo de Item
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'documento', label: 'Documento', icon: '📄' },
                { value: 'objeto_pequeno', label: 'Objeto Pequeno', icon: '📦' },
                { value: 'encomenda_leve', label: 'Encomenda Leve', icon: '🎁' }
              ].map((item) => (
                <Button
                  key={item.value}
                  type="button"
                  onClick={() => handleInputChange('item_type', item.value)}
                  className={`p-3 h-auto flex flex-col items-center ${
                    formData.item_type === item.value
                      ? 'levo-button-primary'
                      : 'levo-button-secondary'
                  }`}
                >
                  <span className="text-2xl mb-1">{item.icon}</span>
                  <span className="text-xs">{item.label}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Item Description */}
        <Card className="levo-card">
          <CardContent className="p-4">
            <label className="block text-sm font-medium text-white mb-2">
              Descrição do Item (opcional)
            </label>
            <Input
              value={formData.item_description}
              onChange={(e) => handleInputChange('item_description', e.target.value)}
              className="levo-input"
              placeholder="Descreva brevemente o item..."
            />
          </CardContent>
        </Card>

        {/* Payment Method */}
        <Card className="levo-card">
          <CardContent className="p-4">
            <label className="block text-sm font-medium text-white mb-3">
              Método de Pagamento
            </label>
            <div className="space-y-2">
              {[
                { value: 'pix', label: 'PIX', icon: '💳' },
                { value: 'card', label: 'Cartão', icon: '💳' },
                { value: 'wallet', label: 'Carteira Digital', icon: '📱' }
              ].map((method) => (
                <Button
                  key={method.value}
                  type="button"
                  onClick={() => handleInputChange('payment_method', method.value)}
                  className={`w-full flex items-center justify-start p-3 ${
                    formData.payment_method === method.value
                      ? 'levo-button-primary'
                      : 'levo-button-secondary'
                  }`}
                >
                  <span className="text-xl mr-3">{method.icon}</span>
                  <span>{method.label}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Estimate */}
        <Card className="levo-card">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <div className="text-lg font-semibold text-white">
                  Estimativa: R$ {estimatedPrice.toFixed(2)}
                </div>
                <div className="flex items-center levo-text-secondary">
                  <Clock className="w-4 h-4 mr-1" />
                  <span>Tempo: {estimatedTime} min</span>
                </div>
              </div>
              <Package className="w-8 h-8 levo-text-primary" />
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <Button
          type="submit"
          className="w-full levo-button-primary h-14 text-xl font-bold"
        >
          Solicitar Entrega
        </Button>
      </form>
    </div>
  )
}

export default DeliveryRequest

