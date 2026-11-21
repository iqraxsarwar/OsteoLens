export default function WelcomeCard({ name }) { 
  return ( 
    <section style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}> 
      <h2>Welcome, {name}!</h2> 
      <p>This is a reusable component under <code>src/components</code>.</p> 
    </section> 
  ); 
}