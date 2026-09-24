#include "WarDevelopmentAccount.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
    TSharedPtr<FJsonObject> ResponseObject(const FHttpResponsePtr& Response)
    {
        TSharedPtr<FJsonObject> Value;
        if (Response && Response->GetContentLength() < 65536)
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response->GetContentAsString()), Value);
        return Value;
    }
}

bool UWarDevelopmentAccount::IsAllowedLoginUrl(const FString& Url)
{
    return Url.StartsWith(TEXT("https://mfwnnvnvchwureeckdfx.supabase.co/auth/v1/authorize?"))
        && !Url.Contains(TEXT("\r")) && !Url.Contains(TEXT("\n"));
}

void UWarDevelopmentAccount::BeginLogin()
{
#if UE_BUILD_SHIPPING
    Status = TEXT("Development authentication is unavailable in this build.");
#else
    if (bPolling) return;
    const uint64 Generation = ++LoginGeneration;
    if (LocalKey.IsEmpty()) LocalKey = FGuid::NewGuid().ToString(EGuidFormats::Digits) + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    bApproved = false; AccessToken.Reset(); AccountId.Reset();
    Status = TEXT("Starting development sign-in...");
    auto Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(TEXT("http://127.0.0.1:43871/login")); Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + LocalKey); Request->SetTimeout(10);
    TWeakObjectPtr<UWarDevelopmentAccount> Weak(this);
    Request->OnProcessRequestComplete().BindLambda([Weak, Generation](FHttpRequestPtr, FHttpResponsePtr Response, bool Success) {
        if (!Weak.IsValid() || Weak->LoginGeneration != Generation) return;
        auto Json = ResponseObject(Response); FString Url;
        if (!Success || !Response || Response->GetResponseCode() != 200 || !Json
            || !Json->TryGetStringField(TEXT("url"), Url) || !IsAllowedLoginUrl(Url))
        { Weak->Status = TEXT("Sign-in unavailable. Start the development login companion and check GitHub configuration."); return; }
        Weak->Status = TEXT("Complete GitHub sign-in in your browser."); Weak->bPolling = true;
        Weak->Deadline = FPlatformTime::Seconds() + 300;
        FPlatformProcess::LaunchURL(*Url, nullptr, nullptr);
        if (UWorld* World = Weak->GetWorld()) World->GetTimerManager().SetTimer(Weak->LoginTimer, Weak.Get(), &UWarDevelopmentAccount::PollLogin, 1.f, true);
    });
    Request->ProcessRequest();
#endif
}

void UWarDevelopmentAccount::PollLogin()
{
#if !UE_BUILD_SHIPPING
    if (!bPolling || FPlatformTime::Seconds() > Deadline)
    {
        bPolling = false; Status = TEXT("Sign-in timed out. Try again.");
        if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(LoginTimer);
        return;
    }
    auto Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(TEXT("http://127.0.0.1:43871/session")); Request->SetVerb(TEXT("GET"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + LocalKey); Request->SetTimeout(5);
    TWeakObjectPtr<UWarDevelopmentAccount> Weak(this);
    const uint64 Generation = LoginGeneration;
    Request->OnProcessRequestComplete().BindLambda([Weak, Generation](FHttpRequestPtr, FHttpResponsePtr Response, bool Success) {
        if (!Weak.IsValid() || Weak->LoginGeneration != Generation || !Weak->bPolling) return;
        const auto Json = ResponseObject(Response); FString Token; bool Pending = true;
        if (!Success || !Json || !Response || Response->GetResponseCode() != 200) return;
        Json->TryGetBoolField(TEXT("pending"), Pending);
        if (Pending || !Json->TryGetStringField(TEXT("accessToken"), Token) || Token.IsEmpty()) return;
        Weak->AccessToken = Token; Weak->bPolling = false;
        if (Weak->GetWorld()) Weak->GetWorld()->GetTimerManager().ClearTimer(Weak->LoginTimer);
        Weak->VerifyGateway();
    });
    Request->ProcessRequest();
#endif
}

void UWarDevelopmentAccount::VerifyGateway()
{
#if !UE_BUILD_SHIPPING
    const FString Gateway = FPlatformMisc::GetEnvironmentVariable(TEXT("AEGIS_DEV_GATEWAY_URL"));
    if (!Gateway.StartsWith(TEXT("https://")) || Gateway.Contains(TEXT("?")) || Gateway.Contains(TEXT("#")))
    { Status = TEXT("GitHub sign-in completed. Configure the development gateway to request project access."); return; }
    auto Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Gateway / TEXT("session")); Request->SetVerb(TEXT("GET"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + AccessToken); Request->SetTimeout(10);
    TWeakObjectPtr<UWarDevelopmentAccount> Weak(this);
    const uint64 Generation = LoginGeneration;
    Request->OnProcessRequestComplete().BindLambda([Weak, Generation](FHttpRequestPtr, FHttpResponsePtr Response, bool Success) {
        if (!Weak.IsValid() || Weak->LoginGeneration != Generation) return;
        const auto Json = ResponseObject(Response); const TSharedPtr<FJsonObject>* Data = nullptr;
        FString MemberStatus, UserId;
        if (!Success || !Response || Response->GetResponseCode() != 200 || !Json
            || !Json->TryGetObjectField(TEXT("data"), Data) || !Data
            || !(*Data)->TryGetStringField(TEXT("status"), MemberStatus)
            || !(*Data)->TryGetStringField(TEXT("userId"), UserId))
        { Weak->Status = TEXT("Could not verify development access. Check the project network and gateway."); return; }
        Weak->AccountId = UserId; Weak->bApproved = MemberStatus == TEXT("approved");
        Weak->Status = Weak->bApproved ? TEXT("Developer account approved. Shared server admission is still under development.")
            : MemberStatus == TEXT("pending") ? TEXT("Awaiting approval from the project owner.") : TEXT("Development access has been revoked.");
    });
    Request->ProcessRequest();
#endif
}

void UWarDevelopmentAccount::Logout()
{
    ++LoginGeneration;
    bPolling = false; bApproved = false; AccessToken.Reset(); AccountId.Reset();
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(LoginTimer);
#if !UE_BUILD_SHIPPING
    if (!LocalKey.IsEmpty())
    {
        auto Request = FHttpModule::Get().CreateRequest();
        Request->SetURL(TEXT("http://127.0.0.1:43871/logout")); Request->SetVerb(TEXT("POST"));
        Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + LocalKey); Request->SetTimeout(5); Request->ProcessRequest();
    }
#endif
    Status = TEXT("Signed out of development.");
}
void UWarDevelopmentAccount::Deinitialize() { Logout(); LocalKey.Reset(); Super::Deinitialize(); }

void UWarDevelopmentAccount::GatewayRequest(const FString& Method,const FString& Path,const FString& Body,TFunction<void(int32,const FString&)> Complete)
{
#if UE_BUILD_SHIPPING
    Complete(403,TEXT("Development authoring is unavailable in Shipping."));
#else
    const FString Gateway=FPlatformMisc::GetEnvironmentVariable(TEXT("AEGIS_DEV_GATEWAY_URL"));
    if (!bApproved || AccessToken.IsEmpty() || !Gateway.StartsWith(TEXT("https://")) || Gateway.Contains(TEXT("?")) || Gateway.Contains(TEXT("#"))
        || Path.Contains(TEXT("..")) || Path.Contains(TEXT("\r")) || Path.Contains(TEXT("\n")) || !(Path==TEXT("operations") || Path.StartsWith(TEXT("abilities/"))) || Body.Len()>8000000)
    { Complete(403,TEXT("Approved development sign-in and an HTTPS gateway are required.")); return; }
    const uint64 Generation=LoginGeneration; TWeakObjectPtr<UWarDevelopmentAccount> Weak(this);
    auto Request=FHttpModule::Get().CreateRequest(); Request->SetURL(Gateway/Path); Request->SetVerb(Method);
    Request->SetHeader(TEXT("Authorization"),TEXT("Bearer ")+AccessToken); Request->SetHeader(TEXT("Content-Type"),TEXT("application/json")); Request->SetContentAsString(Body); Request->SetTimeout(15);
    Request->OnProcessRequestComplete().BindLambda([Weak,Generation,Complete](FHttpRequestPtr,FHttpResponsePtr Response,bool Success) {
        if (!Weak.IsValid() || Weak->LoginGeneration!=Generation) { Complete(401,TEXT("Sign-in changed; reconcile this request after signing in.")); return; }
        if (!Success || !Response || Response->GetContentLength()>9000000) { Complete(0,TEXT("Connection lost. The operation may have committed; retry the same request.")); return; }
        Complete(Response->GetResponseCode(),Response->GetContentAsString());
    });
    if (!Request->ProcessRequest()) Complete(0,TEXT("Gateway request could not start."));
#endif
}
