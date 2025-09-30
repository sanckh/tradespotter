import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { TrendingUp, TrendingDown, User, Calendar, DollarSign } from 'lucide-react'
import { format } from 'date-fns'

interface Trade {
  id: string
  transaction_date: string | null
  published_at: string | null
  ticker?: string | null
  asset_name: string
  side: string | null
  amount_range: string | null
  notes?: string | null
  politicians: {
    id: string
    full_name: string
    state: string | null
    chamber: string | null
  }
}

interface TradeCardProps {
  trade: Trade
}

const TradeCard = ({ trade }: TradeCardProps) => {
  const getTransactionIcon = (side: string | null) => {
    switch (side?.toLowerCase()) {
      case 'buy':
        return <TrendingUp className="h-4 w-4 text-success" />
      case 'sell':
        return <TrendingDown className="h-4 w-4 text-destructive" />
      default:
        return <DollarSign className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getTransactionColor = (side: string | null) => {
    switch (side?.toLowerCase()) {
      case 'buy':
        return 'bg-success/10 text-success border-success/20'
      case 'sell':
        return 'bg-destructive/10 text-destructive border-destructive/20'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  const formatSide = (side: string | null) => {
    if (!side) return 'Unknown'
    return side.charAt(0).toUpperCase() + side.slice(1).toLowerCase()
  }


  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarFallback>
                <User className="h-5 w-5" />
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-base">{trade.politicians.full_name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">
                  {trade.politicians.state && trade.politicians.chamber 
                    ? `${trade.politicians.state} • ${trade.politicians.chamber}`
                    : trade.politicians.state || trade.politicians.chamber || 'N/A'}
                </span>
              </div>
            </div>
          </div>
          <Badge variant="outline" className={getTransactionColor(trade.side)}>
            {getTransactionIcon(trade.side)}
            {formatSide(trade.side)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              {trade.ticker ? `${trade.ticker} - ` : ''}{trade.asset_name}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{trade.amount_range}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-3">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Trade: {trade.transaction_date ? format(new Date(trade.transaction_date), 'MMM dd, yyyy') : 'N/A'}
          </div>
          <div>
            Published: {trade.published_at ? format(new Date(trade.published_at), 'MMM dd, yyyy') : 'N/A'}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default TradeCard