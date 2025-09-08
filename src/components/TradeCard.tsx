import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { TrendingUp, TrendingDown, User, Calendar, DollarSign } from 'lucide-react'
import { format } from 'date-fns'

interface Trade {
  id: string
  transaction_date: string
  disclosure_date: string
  ticker?: string
  asset_description: string
  asset_type: string
  transaction_type: string
  amount_range: string
  congress_members: {
    id: string
    full_name: string
    party: string
    state: string
    chamber: string
    photo_url?: string
  }
}

interface TradeCardProps {
  trade: Trade
}

const TradeCard = ({ trade }: TradeCardProps) => {
  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'Purchase':
        return <TrendingUp className="h-4 w-4 text-success" />
      case 'Sale':
        return <TrendingDown className="h-4 w-4 text-destructive" />
      default:
        return <DollarSign className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getTransactionColor = (type: string) => {
    switch (type) {
      case 'Purchase':
        return 'bg-success/10 text-success border-success/20'
      case 'Sale':
        return 'bg-destructive/10 text-destructive border-destructive/20'
      default:
        return 'bg-muted text-muted-foreground'
    }
  }

  const getPartyColor = (party: string) => {
    switch (party) {
      case 'Republican':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'Democrat':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarImage src={trade.congress_members.photo_url} alt={trade.congress_members.full_name} />
              <AvatarFallback>
                <User className="h-5 w-5" />
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-base">{trade.congress_members.full_name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={getPartyColor(trade.congress_members.party)}>
                  {trade.congress_members.party}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {trade.congress_members.state} • {trade.congress_members.chamber}
                </span>
              </div>
            </div>
          </div>
          <Badge variant="outline" className={getTransactionColor(trade.transaction_type)}>
            {getTransactionIcon(trade.transaction_type)}
            {trade.transaction_type}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              {trade.ticker ? `${trade.ticker} - ` : ''}{trade.asset_description}
            </span>
            <Badge variant="secondary">{trade.asset_type}</Badge>
          </div>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{trade.amount_range}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-3">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Trade: {format(new Date(trade.transaction_date), 'MMM dd, yyyy')}
          </div>
          <div>
            Disclosed: {format(new Date(trade.disclosure_date), 'MMM dd, yyyy')}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default TradeCard