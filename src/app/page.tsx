'use client';

import Banner from '@/components/Banner';
import SelectionPanel from '@/components/SelectionPanel';

function App() {
  return (
    <>
      <Banner />
      <div className="mx-auto w-full max-w-[90rem] px-4 pt-4 sm:px-6 lg:pt-6">
        <SelectionPanel />
      </div>
    </>
  );
}

export default App;
