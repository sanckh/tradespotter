import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/use-toast'
import { Search, TrendingUp, Users, Bell, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button';
import { useNavigate } from "react-router-dom";

interface HeaderProps {
  /** The main title of the page */
  title: string;
  /** Optional subtitle text */
  subtitle?: string;
 /** Whether to show the app logo as clickable (defaults to true) */
  showClickableLogo?: boolean;
  /** Custom logo click handler (defaults to navigate to home) */
  onLogoClick?: () => void;
}

const Header = ({
    title,
    subtitle,
    showClickableLogo = true,
    onLogoClick 
}: HeaderProps) => {
    const { user, signOut, loading: authLoading } = useAuth();
    const { toast } = useToast();
    const navigate = useNavigate();

    const handleSignOut = async () => {
        await signOut()
        toast({
        title: "Signed out",
        description: "You have been successfully signed out"
        })
    };

    const handleLogoClick = () => {
        if (onLogoClick) {
        onLogoClick();
        } else {
        navigate('/home');
        }
    };

      return (
        <header className="border-b bg-background">
            <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
          {/* Logo and Title Section */}
          <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
            <div 
              className={`w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg flex items-center justify-center flex-shrink-0 ${
                showClickableLogo ? 'cursor-pointer hover:from-blue-700 hover:to-blue-900 transition-colors touch-manipulation' : ''
              }`}
              onClick={showClickableLogo ? handleLogoClick : undefined}
            >
              <TrendingUp className="h-4 w-4 sm:h-6 sm:w-6 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-lg sm:text-xl lg:text-2xl font-bold bg-gradient-to-r from-blue-700 to-amber-600 bg-clip-text text-transparent truncate">
                {title}
              </h1>
              {subtitle && (
                <p className="text-xs sm:text-sm text-blue-600 truncate">
                  {subtitle}
                </p>
              )}
            </div>
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
  );
};

export default Header;
