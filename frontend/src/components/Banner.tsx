'use client';

import { useState } from "react";
import Image from "next/image";
import logo from "@/assets/Logo.png";

const Banner = () => {
  const [showReportForm, setShowReportForm] = useState(false);

  const openReportForm = () => setShowReportForm(true);
  const closeReportForm = () => setShowReportForm(false);

  return (
    <>
      {/* === Header Wrapper (full width, black background) === */}
      <header className="z-50 w-full bg-black shadow-md sm:shadow-none">
        <div className="w-full px-4 py-3 sm:px-6 sm:py-4 lg:px-[35px] lg:py-5">

          {/* 
            Flex layout for the header content.
            justify-between pushes logo to the left and buttons to the right.
          */}
          <div className="flex w-full items-center justify-between">

            {/* === Left Logo Section === */}
            <div className="flex items-center gap-3">
              <Image
                src={logo}
                alt="Shipnoise Logo"
                width={38.09}
                height={40}
                className="object-contain"
                priority
              />
              <h1
                className="text-white text-[22px] font-bold sm:text-[24px]"
                style={{ fontFamily: 'Mukta, sans-serif' }}
              >
                Shipnoise
              </h1>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-4 gap-3">

              {/* Improve Shipnoise button */}
              <a
                href="https://mailchi.mp/7ce0cea69cd0/help-improve-shipnoise"
                target="_blank"
                rel="noreferrer"
                className="flex h-[38px] items-center justify-center rounded-[100px] bg-white text-[15px] font-medium text-black transition hover:bg-slate-100 sm:w-[224px]"
                style={{ fontFamily: 'Montserrat, sans-serif' }}
              >
                Help improve Shipnoise!
              </a>

              {/* Report problem button */}
              <button
                type="button"
                onClick={openReportForm}
                className="flex h-[38px] items-center justify-center rounded-[100px] border border-white bg-transparent text-[15px] font-medium text-white transition hover:bg-white/10 sm:w-[232px] cursor-pointer"
                style={{ fontFamily: 'Montserrat, sans-serif' }}
              >
                Report Technical Problem
              </button>
            </div>

          </div>
        </div>
      </header>

      {/* === Popup Form Overlay === */}
      {showReportForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-10">

          {/* Modal box */}
          <div className="relative w-full max-w-[760px] h-full max-h-[90vh] rounded-2xl bg-white shadow-2xl overflow-hidden">

            {/* Close Button */}
            <button
              type="button"
              onClick={closeReportForm}
              className="absolute right-4 top-4 rounded-full bg-black/70 px-3 py-1 text-sm font-medium text-white cursor-pointer"
              style={{ fontFamily: 'Montserrat, sans-serif' }}
            >
              Close
            </button>

            {/* Embedded Tally form */}
            <iframe
              title="Report Technical Problem"
              src="https://tally.so/embed/3E4Z6X?hideTitle=1&transparentBackground=1&formEventsForwarding=1"
              className="h-full w-full border-0"
              allow="fullscreen"
            />
          </div>
        </div>
      )}
    </>
  );
};

export default Banner;
