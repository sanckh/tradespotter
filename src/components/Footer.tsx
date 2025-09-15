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
          <footer>
          <div className="container mx-auto px-5 py-5">
          <div className="flex items-center">
              <span className="text-sm text-muted-foreground disclaimerInfo" style={{ marginLeft: "20px", marginRight: "20px"}}>
                The information provided on this site is for informational purposes only and does not constitute investment advice, financial advice, trading advice, or any other form of advice. We make no guarantees regarding the accuracy, timeliness, or completeness of the information. You are solely responsible for any investment decisions you make, and you agree that this site and its operators are not liable for any losses or damages that may arise from your use of the information provided.
              </span>
          </div>
        </div>
      </footer>
  );
};

export default Footer;