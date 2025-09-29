import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import { User, BookOpen, ArrowLeft, Bell, Crown, CreditCard, Trash2, AlertTriangle, Info, Clock, ChevronDown } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const Settings = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("profile");

    // Stub function so it compiles — replace with actual implementation later
    const setFullName = (value: string) => {
        // TODO: setFullName here
        console.log("setFullName called with:", value);
    };

    const handleUpdateProfile = () => {
        // TODO: handleUpdateProfile here
        console.log("handleUpdateProfile called");
    };
  
  // User timezone state
  const [timezone, setTimezone] = useState("");
  const [timezones, setTimezones] = useState<string[]>([]);
  const [loadingTimezone, setLoadingTimezone] = useState(true);
  
  // Get available timezones and user's timezone
  useEffect(() => {
    // Get list of timezones using Intl API
      // TypeScript might not recognize supportedValuesOf yet, so we use any
      const tzNames = (Intl as any).supportedValuesOf?.('timeZone') || [];
      if (tzNames.length > 0) {
        setTimezones(tzNames);
      } else {
        throw new Error('No timezones returned');
      }
    
    // Get user's timezone
    const fetchTimezone = async () => {
      if (!user?.id) return;
      
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('timezone')
          .eq('id', user.id)
          .single();
        
        if (error) throw error;
        
        // If no timezone set yet, use browser's timezone
        // Since the migration might not be applied yet, handle missing timezone field
        setTimezone((data as any)?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
      } catch (error) {
        console.error('Error fetching timezone:', error);
        // Default to browser timezone if available
        setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
      } finally {
        setLoadingTimezone(false);
      }
    };
    
    fetchTimezone();
  }, [user?.id]);

  const handleUpdateTimezone = async (selectedTimezone: string) => {
    if (!user?.id || timezone === selectedTimezone) return;
    
    try {
      setTimezone(selectedTimezone);
      // Cast to any to bypass TypeScript checking until migration is applied
      const { error } = await supabase
        .from('profiles')
        .update({ timezone: selectedTimezone } as any)
        .eq('id', user.id);
      
      if (error) throw error;
      
      toast.success("Timezone updated successfully");
    } catch (error) {
      console.error("Error updating timezone:", error);
      toast.error("Failed to update timezone");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50">
      <Header 
        title="Settings"
        subtitle="Manage your account and preferences"
      />

      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 max-w-4xl">
        {/* Page Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-blue-900">Account Settings</h2>
          <p className="text-blue-600">Manage your profile, preferences and account settings</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          {/* Mobile Dropdown */}
          <div className="block sm:hidden mb-4">
            <Select value={activeTab} onValueChange={setActiveTab}>
              <SelectTrigger className="w-full bg-white border-slate-200 shadow-sm">
                <SelectValue placeholder="Select a setting" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="profile" className="flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span>Profile</span>
                  </div>
                </SelectItem>
                <SelectItem value="subscription" className="flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Crown className="h-4 w-4" />
                    <span>Subscription</span>
                  </div>
                </SelectItem>
                <SelectItem value="notifications" className="flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4" />
                    <span>Notifications</span>
                  </div>
                </SelectItem>
                <SelectItem value="danger" className="flex items-center gap-2 text-red-600">
                  <div className="flex items-center gap-2">
                    <Trash2 className="h-4 w-4" />
                    <span>Delete Account</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Desktop Tabs */}
          <TabsList className="hidden sm:grid w-full grid-cols-5 h-auto p-1 gap-1 bg-slate-100">
            <TabsTrigger value="profile" className="flex items-center justify-center gap-2 text-sm py-3 px-3 min-h-[44px] data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <User className="h-4 w-4" />
              <span>Profile</span>
            </TabsTrigger>
            <TabsTrigger value="subscription" className="flex items-center justify-center gap-2 text-sm py-3 px-3 min-h-[44px] data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Crown className="h-4 w-4" />
              <span>Subscription</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center justify-center gap-2 text-sm py-3 px-3 min-h-[44px] data-[state=active]:bg-white data-[state=active]:shadow-sm">
              <Bell className="h-4 w-4" />
              <span>Notifications</span>
            </TabsTrigger>
            <TabsTrigger value="danger" className="flex items-center justify-center gap-2 text-sm py-3 px-3 min-h-[44px] text-red-600 data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-red-600">
              <Trash2 className="h-4 w-4" />
              <span>Delete Account</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile Settings */}
          <TabsContent value="profile" className="space-y-6">
            <Card>
              <CardHeader className="pb-4 sm:pb-6 px-4 sm:px-6">
                <CardTitle className="text-lg sm:text-xl">Profile Information</CardTitle>
                <CardDescription className="text-sm">
                  Update your personal information and account details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 px-4 sm:px-6">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    value={user?.email || ""}
                    disabled
                    className="bg-gray-50 h-11 text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Email cannot be changed
                  </p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="fullName" className="text-sm font-medium">Full Name</Label>
                  <Input
                    id="fullName"
                    value=""
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Enter your full name"
                    className="h-11 text-sm"
                  />
                </div>

                <Button 
                  onClick={handleUpdateProfile} 
                  disabled={isLoading}
                  className="w-full h-11 text-sm font-medium mt-6"
                >
                  {isLoading ? "Updating..." : "Update Profile"}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-4 sm:pb-6">
                <CardTitle className="text-lg sm:text-xl">Change Password</CardTitle>
                <CardDescription className="text-sm">
                  Update your password to keep your account secure
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 sm:space-y-4 px-4 sm:px-6">
                update password stuff goes here
              </CardContent>
            </Card>
          </TabsContent>

          {/* Subscription Management */}
          <TabsContent value="subscription" className="space-y-6">
            <Card>
              <CardHeader className="px-4 sm:px-6">
                <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
                  <Crown className="h-5 w-5" />
                  Subscription Status
                </CardTitle>
                <CardDescription className="text-sm">
                  Manage your subscription and billing preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6 px-4 sm:px-6">
                Subscription stuff goes here
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notification Preferences */}
          <TabsContent value="notifications" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Configure how and when you want to receive notifications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                notification stuff goes here
              </CardContent>
            </Card>
          </TabsContent>

          {/* Danger Zone */}
          <TabsContent value="danger" className="space-y-6">
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-600">
                  <Trash2 className="h-5 w-5" />
                  Delete Account
                </CardTitle>
                <CardDescription>
                  Permanently delete your account and all associated data. This action cannot be undone.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                delete stuff goes here
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <Footer />
    </div>
  );
};

export default Settings;