import { Card, CardContent } from "@/components/ui/card";
import Footer from "@/components/Footer";
import Header from "@/components/Header";

const PrivacyPolicy = () => {

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50 flex flex-col">
      <Header 
        title="Privacy Policy" 
        subtitle="How we protect and handle your data" 
      />
      <div className="container mx-auto px-3 sm:px-4 py-6 sm:py-8 flex-1">
        <div className="max-w-4xl mx-auto">

          <Card className="bg-white/60 backdrop-blur-sm border-blue-100">
            <CardContent className="prose prose-blue max-w-none space-y-6">
              <div className="text-blue-600 text-sm mb-6">
                Last updated: September 22, 2025
              </div>

              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Information We Collect</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We collect information that you provide directly to us, including:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Account information (name, email, and optional phone number for SMS alerts)</li>
                  <li>• Notification preferences (which legislators you track, and alert delivery options)</li>
                  <li>• Payment information (processed securely through our payment provider, such as Stripe, if you subscribe to premium features)</li>
                  <li>• Usage data (e.g., login activity, page interactions, notification history)</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">How We Use Your Information</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We use the collected information to:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Deliver trade disclosure notifications by email or SMS according to your preferences</li>
                  <li>• Manage your account and authentication</li>
                  <li>• Process subscription payments</li>
                  <li>• Send important service updates (such as policy changes or downtime notices)</li>
                  <li>• Analyze usage trends to improve the service</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Data Security</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We implement appropriate security measures to protect your personal information, including:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Encryption of sensitive data in transit and at rest</li>
                  <li>• Regular security reviews and monitoring</li>
                  <li>• Secure third-party services for payments and SMS delivery</li>
                  <li>• Limited access to personal data by authorized personnel only</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Data Sharing</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We do not sell your personal information. We may share your information with:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Service providers that help deliver notifications (e.g., email or SMS providers)</li>
                  <li>• Payment processors (e.g., Stripe) for billing purposes</li>
                  <li>• Legal authorities if required by law or to protect our rights</li>
                  <li>• Other third parties, but only with your explicit consent</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Your Rights</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  You have the right to:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Access and review your personal data</li>
                  <li>• Correct inaccurate or outdated data</li>
                  <li>• Request deletion of your account and associated data</li>
                  <li>• Export your tracking and notification preferences</li>
                  <li>• Opt-out of non-essential communications</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Cookies and Tracking</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We use cookies and similar technologies to:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Keep you signed in securely</li>
                  <li>• Remember your preferences and settings</li>
                  <li>• Analyze site usage and performance</li>
                  <li>• Improve functionality and user experience</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Contact Us</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  For privacy-related questions or concerns, please contact us{" "}
                  <a href="mailto:corey.sutton7@gmail.com" className="text-blue-600 hover:text-blue-800 underline">
                    here
                  </a>
                  .
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

export default PrivacyPolicy;