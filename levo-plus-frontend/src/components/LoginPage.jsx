import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import logoImage from '../assets/Levo+_logo_concept.png'

const LoginPage = () => {
  const [userType, setUserType] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const handleUserTypeSelection = (type) => {
    setUserType(type)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    
    // Simulate login - in real app, this would call the backend
    if (email && password) {
      if (userType === 'client') {
        navigate('/client')
      } else if (userType === 'delivery-person') {
        navigate('/delivery-person')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 levo-bg-dark">
      <Card className="w-full max-w-md levo-card">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <img src={logoImage} alt="Levo+ Logo" className="w-32 h-32 object-contain" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">Levo+</CardTitle>
          <p className="levo-text-secondary">Entregas Rápidas</p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {!userType ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white text-center">
                Escolha seu perfil
              </h3>
              <div className="space-y-3">
                <Button
                  onClick={() => handleUserTypeSelection('client')}
                  className="w-full levo-button-secondary h-12 text-lg"
                >
                  Sou Cliente
                </Button>
                <Button
                  onClick={() => handleUserTypeSelection('delivery-person')}
                  className="w-full levo-button-secondary h-12 text-lg"
                >
                  Sou Entregador
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="text-center mb-4">
                <h3 className="text-lg font-semibold text-white">
                  {userType === 'client' ? 'Login Cliente' : 'Login Entregador'}
                </h3>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    E-mail
                  </label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="levo-input"
                    placeholder="seu@email.com"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Senha
                  </label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="levo-input"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-3 pt-4">
                <Button
                  type="submit"
                  className="w-full levo-button-primary h-12 text-lg font-bold"
                >
                  ENTRAR
                </Button>
                
                <Button
                  type="button"
                  onClick={() => setUserType('')}
                  className="w-full levo-button-secondary"
                >
                  Voltar
                </Button>
              </div>
              
              <div className="text-center pt-4">
                <a href="#" className="levo-text-primary text-sm hover:underline">
                  Criar conta
                </a>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default LoginPage

