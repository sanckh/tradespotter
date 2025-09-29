import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { BookOpen, Mail } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";

const Footer = () => {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  return (
    <footer className="bg-gradient-to-br from-blue-900 to-blue-800 text-white mt-auto">
      <div className="container mx-auto px-4 py-6 sm:py-8">
        {/* Main Footer Content */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6 mb-6">

          {/* Legal Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-amber-400">Legal</h3>
            <ul className="space-y-2">
              <li>
                <Link 
                  to="/terms-of-service" 
                  className="text-blue-100 hover:text-white transition-colors text-sm"
                >
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link 
                  to="/privacy-policy" 
                  className="text-blue-100 hover:text-white transition-colors text-sm"
                >
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link 
                  to="/refund-policy" 
                  className="text-blue-100 hover:text-white transition-colors text-sm"
                >
                  Refund Policy
                </Link>
              </li>
            </ul>
          </div>

          {/* Support Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-amber-400">Support</h3>
            <ul className="space-y-2">
              <li>
                <a 
                  href="mailto:corey.sutton7@gmail.com"
                  className="text-blue-100 hover:text-white transition-colors text-sm flex items-center gap-1"
                >
                  <Mail className="h-3 w-3" />
                  Email Support
                </a>
              </li>
            </ul>
          </div>
        
        {/* Bottom Section */}
        <div className="border-t border-blue-700 pt-4">
          <div className="flex flex-col items-center justify-center gap-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-amber-400" />
              <p className="text-blue-200 text-sm">
                © 2025 TradeSpotter. All rights reserved.
              </p>
            </div>
            <p className="text-blue-300 text-xs">
              VERSION PLACEHOLDER
            </p>
          </div>
        </div>
      </div>
      </div>
    </footer>
  );
};

export default Footer;