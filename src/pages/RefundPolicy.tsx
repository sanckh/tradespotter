import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Footer from "@/components/Footer";
import Header from "@/components/Header";

const RefundPolicy = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50 flex flex-col">
      <Header 
        title="Refund Policy" 
        subtitle="Our commitment to customer satisfaction" 
      />
      <div className="container mx-auto px-3 sm:px-4 py-6 sm:py-8 flex-1">
        <div className="max-w-4xl mx-auto">

          <Card className="bg-white/60 backdrop-blur-sm border-blue-100">
            <CardContent className="prose prose-blue max-w-none space-y-6">
              <div className="text-blue-600 text-sm mb-6">
                Last updated: September 22, 2025
              </div>
            
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">30-Day Limited Money-Back Guarantee</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We offer refunds within 30 days of purchase for the following qualifying reasons:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Technical issues preventing access to core features</li>
                  <li>• Service not meeting advertised capabilities</li>
                  <li>• Billing errors or unauthorized charges</li>
                </ul>
              </section>
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Eligibility for Refunds</h3>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Subscription must be cancelled within 30 days of purchase</li>
                  <li>• Refund requests must be submitted through our email</li>
                  <li>• One-time refund policy per customer</li>
                  <li>• Valid reason must be provided and verified</li>
                  <li>• Account must not have violated our terms of service</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">How to Request a Refund</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  To request a refund, please contact our support team <a href="mailto:corey.sutton7@gmail.com" className="text-blue-600 hover:text-blue-800 underline">here</a> with:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Account email address</li>
                  <li>• Detailed explanation of the reason for refund request</li>
                  <li>• Date of purchase</li>
                  <li>• Any relevant screenshots or documentation supporting your request</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Processing Time</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  Refund requests are reviewed within 2-3 business days. If approved, refunds are typically processed within 5-7 business days. The time it takes for the refund to appear in your account may vary depending on your payment method and financial institution.
                </p>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Exceptions</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  We reserve the right to decline refund requests that:
                </p>
                <ul className="text-blue-700 text-sm sm:text-base space-y-1 ml-4">
                  <li>• Do not meet our qualifying reasons for refunds</li>
                  <li>• Show evidence of system or policy abuse</li>
                  <li>• Come from accounts with multiple refund attempts</li>
                  <li>• Show extensive usage of the service before requesting a refund</li>
                  <li>• Violate our terms of service</li>
                </ul>
              </section>
              
              <section>
                <h3 className="text-lg font-semibold text-blue-800 mb-3">Contact Us</h3>
                <p className="text-blue-700 text-sm sm:text-base leading-relaxed">
                  If you have any questions about our refund policy or need to request a refund, please contact us{" "}
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

export default RefundPolicy;