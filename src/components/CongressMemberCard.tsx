import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { Heart, HeartOff, User } from 'lucide-react'
import { followPolitician, unfollowPolitician } from '@/api/users'

interface CongressMember {
  id: string
  first_name: string | null
  last_name: string | null
  full_name: string
  state: string | null
  chamber: string | null
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
        await unfollowPolitician(user.id, member.id)

        toast({
          title: "Unfollowed",
          description: `You are no longer following ${member.full_name}`
        })
      } else {
        await followPolitician(user.id, member.id)

        toast({
          title: "Following",
          description: `You are now following ${member.full_name}`
        })
      }
      
      onFollowChange()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred'
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
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
            {member.chamber && (
              <Badge variant="outline" className="text-xs">
                {member.chamber}
              </Badge>
            )}
            {member.state && (
              <span className="text-sm text-muted-foreground">{member.state}</span>
            )}
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