import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { supabase } from '@/integrations/supabase/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { Heart, HeartOff, User } from 'lucide-react'

interface CongressMember {
  id: string
  first_name: string
  last_name: string
  full_name: string
  state: string
  party: string
  chamber: string
  photo_url?: string
}

interface CongressMemberCardProps {
  member: CongressMember
  isFollowing: boolean
  onFollowChange: () => void
}

const CongressMemberCard = ({ member, isFollowing, onFollowChange }: CongressMemberCardProps) => {
  const { user } = useAuth()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)

  const handleFollowToggle = async () => {
    if (!user) {
      toast({
        title: "Authentication required",
        description: "Please sign in to follow members",
        variant: "destructive"
      })
      return
    }

    setIsLoading(true)
    
    try {
      if (isFollowing) {
        const { error } = await supabase
          .from('user_follows')
          .delete()
          .eq('user_id', user.id)
          .eq('member_id', member.id)

        if (error) throw error

        toast({
          title: "Unfollowed",
          description: `You are no longer following ${member.full_name}`
        })
      } else {
        const { error } = await supabase
          .from('user_follows')
          .insert([{
            user_id: user.id,
            member_id: member.id
          }])

        if (error) throw error

        toast({
          title: "Following",
          description: `You are now following ${member.full_name}`
        })
      }
      
      onFollowChange()
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
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
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="flex flex-row items-center space-y-0 pb-4">
        <Avatar className="h-12 w-12 mr-4">
          <AvatarImage src={member.photo_url} alt={member.full_name} />
          <AvatarFallback>
            <User className="h-6 w-6" />
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <CardTitle className="text-lg">{member.full_name}</CardTitle>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="outline" className="text-xs">
              {member.chamber}
            </Badge>
            <Badge className={getPartyColor(member.party)}>
              {member.party}
            </Badge>
            <span className="text-sm text-muted-foreground">{member.state}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Button
          onClick={handleFollowToggle}
          disabled={isLoading || !user}
          variant={isFollowing ? "destructive" : "default"}
          size="sm"
          className="w-full"
        >
          {isFollowing ? (
            <>
              <HeartOff className="h-4 w-4 mr-2" />
              Unfollow
            </>
          ) : (
            <>
              <Heart className="h-4 w-4 mr-2" />
              Follow
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}

export default CongressMemberCard