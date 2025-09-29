import { useState } from "react";
import { User, Settings, LogOut, BookOpen, Trophy, List, Shield, TrendingUp, Crown } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import { useNavigate } from "react-router-dom";
import { useToast } from '@/hooks/use-toast'

const UserMenu = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [isLoading] = useState(false);
  const { toast } = useToast();

    const handleSignOut = async () => {
        await signOut()
        toast({
        title: "Signed out",
        description: "You have been successfully signed out"
        })
    };

    const getInitials = (input: string | null | undefined): string => {
    if (!input) return "U";

    // If it's an email (contains "@"), derive initials from the email prefix
    if (input.includes("@")) {
        const localPart = input.split("@")[0]; // everything before "@"
        return localPart.slice(0, 2).toUpperCase();
    }

    // Otherwise, treat it like a name
    return input
        .trim()
        .split(/\s+/) // split on any whitespace
        .map((word) => word[0]?.toUpperCase() ?? "")
        .join("")
        .slice(0, 2) || "U";
    };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 sm:h-10 sm:w-10 rounded-full min-h-[32px] min-w-[32px] touch-manipulation">
          <Avatar className="h-7 w-7 sm:h-8 sm:w-8">
            <AvatarFallback className="text-xs sm:text-sm">{getInitials(user?.email)}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56 sm:w-64" align="end" forceMount>
        <div className="flex items-center justify-start gap-2 p-3 sm:p-2">
          <div className="flex flex-col space-y-1 leading-none">
            {user?.email && (
              <p className="w-[180px] sm:w-[200px] truncate text-xs sm:text-sm text-muted-foreground">
                {user.email}
              </p>
            )}
          </div>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate("/settings")} className="py-3 sm:py-2">
          <Settings className="mr-2 h-4 w-4" />
          <span className="text-sm sm:text-base">Settings</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleSignOut} disabled={isLoading} className="py-3 sm:py-2">
          <LogOut className="mr-2 h-4 w-4" />
          <span className="text-sm sm:text-base">{isLoading ? "Signing out..." : "Sign out"}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default UserMenu;