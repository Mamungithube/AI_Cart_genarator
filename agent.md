<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Md Mamun - Business Card</title>
    <!-- Font Awesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: #e2e8f0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: 'Montserrat', sans-serif;
        }

        /* Standard Business Card Aspect Ratio Canvas */
        .card {
            width: 600px;
            height: 337.5px;
            background-color: #121c24;
            position: relative;
            overflow: hidden;
            border-radius: 8px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25);
            color: #ffffff;
        }

        /* Circular/Wavy Background Layers */
        .shape-layer-1 {
            position: absolute;
            top: -120px;
            left: -120px;
            width: 480px;
            height: 480px;
            border-radius: 50%;
            background-color: #1c2b36;
            z-index: 1;
        }

        .shape-layer-2 {
            position: absolute;
            top: -135px;
            left: -135px;
            width: 460px;
            height: 460px;
            border-radius: 50%;
            background: linear-gradient(135deg, #7cc129 0%, #4c8a11 100%);
            z-index: 2;
        }

        .shape-layer-3 {
            position: absolute;
            top: -150px;
            left: -150px;
            width: 440px;
            height: 440px;
            border-radius: 50%;
            background-color: #ffffff;
            z-index: 3;
        }

        /* Bottom Decorative Wave Accent */
        .bottom-accent-1 {
            position: absolute;
            bottom: -160px;
            left: -80px;
            width: 320px;
            height: 320px;
            border-radius: 50%;
            background-color: #1c2b36;
            z-index: 1;
        }

        .bottom-accent-2 {
            position: absolute;
            bottom: -175px;
            left: -95px;
            width: 310px;
            height: 310px;
            border-radius: 50%;
            background: linear-gradient(135deg, #7cc129 0%, #4c8a11 100%);
            z-index: 2;
        }

        /* Brand / Logo Section Left */
        .logo-section {
            position: absolute;
            top: 0;
            left: 0;
            width: 250px;
            height: 100%;
            z-index: 4;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding-left: 20px;
            text-align: center;
        }

        .company-name {
            font-size: 22px;
            font-weight: 800;
            color: #121c24;
            letter-spacing: -0.5px;
        }

        .tagline {
            font-size: 10.5px;
            color: #333333;
            font-weight: 500;
            margin-top: 4px;
        }

        /* Content Section Right */
        .content-section {
            position: absolute;
            top: 0;
            right: 0;
            width: 350px;
            height: 100%;
            z-index: 4;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding-left: 30px;
            padding-right: 20px;
        }

        .person-name {
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .job-title {
            font-size: 14px;
            font-weight: 400;
            color: #d0d7de;
            letter-spacing: 0.2px;
        }

        .title-underline {
            width: 60px;
            height: 2px;
            background-color: #ffffff;
            margin-top: 8px;
            margin-bottom: 22px;
        }

        /* Contact Details */
        .contact-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .contact-item {
            display: flex;
            align-items: center;
            font-size: 13px;
            color: #e6edf3;
            font-weight: 500;
        }

        .contact-item i {
            width: 20px;
            font-size: 14px;
            margin-right: 12px;
            text-align: center;
            color: #ffffff;
        }
    </style>
</head>
<body>

    <div class="card">
        <!-- Background Shapes -->
        <div class="shape-layer-1"></div>
        <div class="shape-layer-2"></div>
        <div class="shape-layer-3"></div>
        <div class="bottom-accent-1"></div>
        <div class="bottom-accent-2"></div>

        <!-- Left Brand / Logo Content -->
        <div class="logo-section">
            <div class="company-name">TechVision BD</div>
            <div class="tagline">Your Vision, Our Technology</div>
        </div>

        <!-- Right Profile & Contact Details -->
        <div class="content-section">
            <div class="person-name">Md Mamun</div>
            <div class="job-title">Senior Software Engineer</div>
            <div class="title-underline"></div>

            <div class="contact-list">
                <div class="contact-item">
                    <i class="fa-solid fa-phone"></i>
                    <span>+880 1928-737434</span>
                </div>
                <div class="contact-item">
                    <i class="fa-solid fa-globe"></i>
                    <span>www.techvision.com.bd</span>
                </div>
                <div class="contact-item">
                    <i class="fa-solid fa-envelope"></i>
                    <span>mamun@techvision.com.bd</span>
                </div>
                <div class="contact-item">
                    <i class="fa-solid fa-location-dot"></i>
                    <span>Dhaka, Bangladesh</span>
                </div>
            </div>
        </div>
    </div>

</body>
</html>