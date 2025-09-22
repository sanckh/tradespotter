import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Footer from "@/components/Footer";
import Header from "@/components/Header";

const TermsOfService = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50 flex flex-col">
      <Header 
        title="Terms of Service" 
        subtitle="TradeSpotter policies and agreements" 
      />
      <div className="container mx-auto px-3 sm:px-4 py-6 sm:py-8 flex-1">
        <div className="max-w-4xl mx-auto">

          <Card className="bg-white/60 backdrop-blur-sm border-blue-100">
            <CardContent className="prose prose-blue max-w-none space-y-6">
              <div className="text-blue-600 text-sm mb-6">
                Last updated: September 2025
              </div>

                <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Service Description</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed mb-3">
                    TradeSpotter provides users with tools to monitor and receive alerts
                    regarding financial trade disclosures made by members of the U.S. Senate
                    and House of Representatives. Specifically, the service allows users to:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                    <li>• Create and manage a personal account</li>
                    <li>• Select and track specific person(s) of interest</li>
                    <li>• Receive notifications by email and/or SMS when new disclosures are published</li>
                    <li>• Access historical disclosure data compiled from public sources</li>
                    <li>• Configure preferences for frequency and type of notifications</li>
                </ul>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed mt-3">
                    TradeSpotter does not guarantee the timeliness, completeness, or accuracy
                    of disclosures, as all information is derived from publicly available
                    government sources.
                </p>
                </section>

                <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">User Obligations</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed mb-3">
                    By using TradeSpotter, you agree to:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                    <li>• Provide accurate account information and keep your credentials secure</li>
                    <li>• Use the service only for lawful purposes and in compliance with all applicable laws</li>
                    <li>• Not misuse or attempt to disrupt the platform, including scraping, reverse-engineering, or unauthorized data access</li>
                    <li>• Respect notification limits and not use the service for spam or automated mass distribution</li>
                    <li>• Acknowledge that notifications are informational only and do not constitute financial advice</li>
                </ul>
                </section>

                <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Limitation of Liability</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed mb-3">
                    TradeSpotter is provided "as is" without warranties of any kind, express or
                    implied. To the maximum extent permitted by law, we are not liable for:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                    <li>• Any errors, omissions, or delays in the disclosure data we relay</li>
                    <li>• Missed, late, or duplicate notifications</li>
                    <li>• Financial, investment, or trading decisions made based on our alerts</li>
                    <li>• Service interruptions, system failures, or unauthorized account access</li>
                    <li>• Any damages resulting from use of third-party services (e.g., SMS carriers or email providers)</li>
                </ul>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed mt-3">
                    All notifications and information provided are for informational purposes
                    only. <strong>This does not constitute investment, financial, or legal advice.
                    You should not rely on TradeSpotter to make investment decisions, and we
                    are not responsible for any losses incurred. By using this service, you
                    agree not to hold us liable for investment outcomes.</strong>
                </p>
                </section>
            </CardContent>
          </Card>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default TermsOfService;