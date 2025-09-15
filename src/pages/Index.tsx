import { useState, useEffect } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { supabase } from '@/integrations/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import CongressMemberCard from '@/components/CongressMemberCard'
import TradeCard from '@/components/TradeCard'
import { useToast } from '@/hooks/use-toast'
import { Search, TrendingUp, Users, Bell, LogOut } from 'lucide-react'

const Index = () => {
  const { user, signOut, loading: authLoading } = useAuth()
  const { toast } = useToast()
  const [members, setMembers] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [followedMembers, setFollowedMembers] = useState<Set<string>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (authLoading) return
    
    if (!user) {
      setLoading(false)
      return
    }

    fetchData()
  }, [user, authLoading])

  const fetchData = async () => {
    try {
      // Fetch congress members
      const { data: membersData } = await supabase
        .from('politicians')
        .select('*')
        .order('last_name')

      // Fetch recent trades with member info
      const { data: tradesData } = await supabase
        .from('trades')
        .select(`
          *,
          politicians (
            id,
            full_name,
            party,
            state,
            chamber,
            photo_url
          )
        `)
        .order('transaction_date', { ascending: false })
        .limit(20)

      // Fetch user follows
      if (user) {
        const { data: followsData } = await supabase
          .from('user_follows')
          .select('member_id')
          .eq('user_id', user.id)

        setFollowedMembers(new Set(followsData?.map(f => f.member_id) || []))
      }

      setMembers(membersData || [])
      setTrades(tradesData || [])
    } catch (error: any) {
      toast({
        title: "Error loading data",
        description: error.message,
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFollowChange = () => {
    fetchData()
  }

  const handleSignOut = async () => {
    await signOut()
    toast({
      title: "Signed out",
      description: "You have been successfully signed out"
    })
  }

  const filteredMembers = members.filter(member =>
    member.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    member.state.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse">
            <TrendingUp className="h-8 w-8 mx-auto mb-2 text-primary" />
            <p className="text-muted-foreground">Loading Trade Spotter...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary/5 to-secondary/5">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-4xl mx-auto text-center">
            <TrendingUp className="h-16 w-16 mx-auto mb-6 text-primary" />
            <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              Trade Spotter
            </h1>
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Track publicly disclosed trades by U.S. members of Congress and get real-time alerts when the people you follow make new investments.
            </p>
            
            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <Card>
                <CardHeader>
                  <TrendingUp className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Real-time Tracking</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Monitor congressional trades as they're disclosed to the public
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <Users className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Follow Members</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Follow specific senators and representatives you're interested in
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <Bell className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Instant Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Get SMS and email notifications when followed members make trades
                  </p>
                </CardContent>
              </Card>
            </div>

            <div className="space-x-4">
              <Link to="/auth">
                <Button size="lg" className="text-lg px-8">
                  Get Started
                </Button>
              </Link>
              <Link to="/auth">
                <Button variant="outline" size="lg" className="text-lg px-8">
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-bold">Trade Spotter</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                Welcome back, {user.email}
              </span>
              <Button variant="ghost" size="sm" onClick={handleSignOut}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="dashboard" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="members">Congress Members</TabsTrigger>
            <TabsTrigger value="following">Following ({followedMembers.size})</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6 mt-6">
            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Recent Congressional Trades
                  </CardTitle>
                  <CardDescription>
                    Latest disclosed trades from members of Congress
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {trades.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">
                      No trades have been recorded yet. Check back soon!
                    </p>
                  ) : (
                    <div className="grid gap-4">
                      {trades.map((trade) => (
                        <TradeCard key={trade.id} trade={trade} />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="members" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>All Congress Members</CardTitle>
                <CardDescription>
                  Browse and follow members of Congress to track their trades
                </CardDescription>
                <div className="flex items-center space-x-2">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by name or state..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="max-w-sm"
                  />
                </div>
              </CardHeader>
              <CardContent>
                {filteredMembers.length === 0 && searchTerm ? (
                  <p className="text-muted-foreground text-center py-8">
                    No members found matching "{searchTerm}"
                  </p>
                ) : filteredMembers.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">
                    No congress members have been added yet.
                  </p>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredMembers.map((member) => (
                      <CongressMemberCard
                        key={member.id}
                        member={member}
                        isFollowing={followedMembers.has(member.id)}
                        onFollowChange={handleFollowChange}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="following" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Following</CardTitle>
                <CardDescription>
                  Members you're following - you'll get alerts when they make trades
                </CardDescription>
              </CardHeader>
              <CardContent>
                {followedMembers.size === 0 ? (
                  <div className="text-center py-8">
                    <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-muted-foreground mb-4">
                      You're not following any members yet
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Go to the Congress Members tab to start following members and receive trade alerts
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {members
                      .filter(member => followedMembers.has(member.id))
                      .map((member) => (
                        <CongressMemberCard
                          key={member.id}
                          member={member}
                          isFollowing={true}
                          onFollowChange={handleFollowChange}
                        />
                      ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <footer>
          <div className="container mx-auto px-5 py-5">
          <div className="flex items-center">
              <span className="text-sm text-muted-foreground disclaimerInfo" style={{ marginLeft: "20px", marginRight: "20px"}}>
                The information provided on this site is for informational purposes only and does not constitute investment advice, financial advice, trading advice, or any other form of advice. We make no guarantees regarding the accuracy, timeliness, or completeness of the information. You are solely responsible for any investment decisions you make, and you agree that this site and its operators are not liable for any losses or damages that may arise from your use of the information provided.
              </span>
          </div>
        </div>
      </footer>
    </div>
  )
};

export default Index;
